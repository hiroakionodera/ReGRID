# ReGRID model - Version 8.0


########### Import library ##########
import gurobipy as gp
from gurobipy import GRB
from tqdm import tqdm
import pandas as pd
import csv
import os
import sys


########### Model creation ##########

# Case setting
TERM = '1y' # Analysis term: 1y=Yearly
STEP = 6 # Timestep(h)
VER = 'v8' # Model version
YEAR = int(sys.argv[2]) # Target year
BOUNDARY = 'japan' # Spatial boundary
NETWORK = '1741' # TSN:Transmission, '1741':Municipality
PATHWAY = sys.argv[1] # Socioeconomic and emission pathway: C1:1.5C, C7:below 4C
POTENTIAL_AVAILABILITY = 100 # Uniform availability of renewable energy(%)
POTENTIAL_CASE = sys.argv[4] # Renewable energy potential assumptions ('base':HPA, 'low':PA+OECM, 'mid':Enhanced, 'high':FullProtect)
COST_CASE = 'moderate' # Cost assumption

if int(sys.argv[3]) == 'ccs-biomass':
    TECH_CASE = 'ccs-biomass'
    CCS_AVAILAVILITY = 2 # 0:Not available, 1:Unlimited, 2:Only domestic
    NUCLEAR_AVAILABILITY = 2 # 0:Not available, 1:Available, 2:No new installation
    BIOMASS_CAP = 0.1 # Availability of technical potential
else:
    TECH_CASE = 'opt'
    CCS_AVAILAVILITY = 1 # 0:Not available, 1:Unlimited, 2:Only domestic
    NUCLEAR_AVAILABILITY = 1 # 0:Not available, 1:Available, 2:No new installation
    BIOMASS_CAP = 1 # Availability of technical potential

# Initialize a model
def get_model_name(ver=VER, year=YEAR, pathway=PATHWAY, term=TERM, step=STEP, boundary=BOUNDARY, network=NETWORK, nuclear=NUCLEAR_AVAILABILITY, potential=POTENTIAL_AVAILABILITY, potential_case=POTENTIAL_CASE, cost_case=COST_CASE, tech_case=TECH_CASE):
    return f"ReGRID2_{ver}_{year}_{pathway}_{term}_{step}_{boundary}_{network}_n{nuclear}_p{potential}_{potential_case}_{cost_case}_{tech_case}"

model_name = get_model_name()
model = gp.Model(model_name)
print(model_name)

# Output directory
os.makedirs('output/%s' % model_name, exist_ok=True)

# Log file
model.Params.LogFile = f'output/{model_name}/log_{model_name}.txt'


########### Input data ##########

# Region list
region_list = pd.read_csv('input/region.csv', index_col='code', dtype={'code':str, 'DSN':str, 'pref_code':str})
REGION = region_list.index.to_list() # All nodes
SUBSTATION = pd.read_csv('input/region_substation.csv', index_col=0, dtype={'region':str})['region'].to_list() # Substation nodes
NODE = [r for r in REGION if r not in SUBSTATION] # Terminal nodes
AREA = region_list['DSN'].copy() # Distribution area
REGION06 = pd.Series(data=[f"{r:>6}".replace(' ','_') for r in REGION], index=REGION) # Region list (6 digit code)
SPREGION = {}

if BOUNDARY != 'japan':
    REGION = region_list[region_list['TSO'] == BOUNDARY].index.to_list() # All nodes
    SUBSTATION = [r for r in REGION if r in SUBSTATION] # Substation nodes
    NODE = [r for r in REGION if r not in SUBSTATION] # Terminal nodes
    AREA = region_list[region_list['TSO'] == BOUNDARY]['DSN'].copy() # Distribution area

# Time series list
TIME = pd.read_csv('input/%sh/time_%s.csv' % (STEP,TERM))['time'].to_list()
TIME04 = pd.Series(data=[f"{r:>4}".replace(' ','_') for r in TIME], index=TIME) # Time series (4 digit)
T_LEN = len(TIME)

# Time series scaling
if T_LEN * STEP == 8760:
    T_SCALE = 1
    T_EXPAND = 1
else:
    T_SCALE = (T_LEN * STEP) / 8760
    T_EXPAND = 8760 / (T_LEN * STEP)

# Technology list
RESOURCE = ['hydro','geoth','river','onwin','of-fx','of-fl','solar']
WASTE = ['waste','msw-c']
WOODY = ['woody','beccs']
FOSSIL = ['coalp','coalc','gas-p','gas-c','oil-p']
STORAGE = ['stpmp','stbat']
H2TECH = ['st-h2','el-h2','h2-el']
DACCS = ['daccs']
AUX = ['stpcs','h2cmp']
if NUCLEAR_AVAILABILITY != 0:
    THERMAL = FOSSIL + ['nuclr']
else:
    THERMAL = FOSSIL

# Regional data aggregation
def city_to_substation(data, calc='sum'):
    data = pd.concat([data, AREA], axis=1)
    if calc == 'sum':
        ss_data = data.groupby(['DSN']).sum()
    elif calc == 'mean':
        ss_data = data.groupby(['DSN']).mean()
    return ss_data

# Storage parameter
storage_data = pd.read_csv('input/storage.csv', index_col='code', dtype={'code':str})
storage = city_to_substation(storage_data)

# Scenario data
scenario_data = pd.read_csv('input/scenarios.csv', index_col=0, dtype={'year':str})
scenario = scenario_data[scenario_data['category'] == PATHWAY] # Energy demand and emissions pathway

# CCS scenario
if CCS_AVAILAVILITY == 2:
    ccs_potential = pd.read_csv('input/ccs_potential_low.csv', index_col=['code'], dtype={'code':str})[str(YEAR)]
else:
    ccs_potential = pd.read_csv('input/ccs_potential.csv', index_col=['code'], dtype={'code':str})[str(YEAR)]
SPREGION['ccs'] = [AREA[r] for r in ccs_potential[ccs_potential>0].index.to_list()] # CCS node list

# CO2 emission
co2_cap = scenario['Emissions|CO2|Energy|Supply|Electricity'][str(YEAR)] * 1000000 # MtCO2 -> tCO2

# Population scenario
population = pd.read_csv('input/population.csv', index_col='code', dtype={'code':str})
regional_population_growth = population[str(YEAR)] / population['2020'] # Population growth rate
national_population_growth = sum(population[str(YEAR)]) / sum(population['2020']) # Population growth rate

# Electricity demand
regional_current_demand = pd.read_csv('input/%sh/elect.csv' % (STEP), index_col=0)
national_current_demand = regional_current_demand.sum().sum()
national_future_demand = scenario['Final Energy|Electricity'][str(YEAR)] * 1000000 #TWh -> MWh
regional_future_demand = regional_current_demand * (regional_population_growth / national_population_growth) * (national_future_demand / national_current_demand)
regional_future_demand = regional_future_demand * (national_future_demand / regional_future_demand.sum().sum())
regional_future_demand = regional_future_demand.loc[:,REGION]

# Technology dataset (Cost, Efficiency, etc.)
P = pd.read_csv(f'input/technology/technology_{PATHWAY}.csv', index_col=0)
P = P[(P['year'] == YEAR) & (P['scenario'] == COST_CASE)]

# Renewable energy temporal profiles
profile = {}
profile["solar"] = pd.read_csv('input/%sh/solar_2019.csv' % (STEP), index_col=0)
profile["onwin"] = pd.read_csv('input/%sh/onwind_2019.csv' % (STEP), index_col=0)
profile["of-fx"] = pd.read_csv('input/%sh/ofwind_2019_fixed.csv' % (STEP), index_col=0)
profile["of-fl"] = pd.read_csv('input/%sh/ofwind_2019_float.csv' % (STEP), index_col=0)
profile["river"] = pd.read_csv('input/%sh/river_2019.csv' % (STEP), index_col=0)
profile["geoth"] = pd.read_csv('input/%sh/geothermal_2019.csv' % (STEP), index_col=0)
profile["hydro"] = pd.read_csv('input/%sh/hydro_2019.csv' % (STEP), index_col=0)

# Annual capacity factor for renewables
CF_annual = {}
for res in profile.keys():
    CF_annual[res] = (profile[res] / STEP).mean()

# Renewable energy potential (MW)
potential_VRE_MW = pd.read_csv('input/potential/renewables_potential_MW_%s.csv' % POTENTIAL_CASE, index_col='code', dtype={'code':str})

potential_VRE = pd.DataFrame()
for res in CF_annual.keys():
    potential_VRE[res] = (potential_VRE_MW[res] * CF_annual[res] * 8760) # MW -> MWh
    if res != "hydro":
        potential_VRE[res] = potential_VRE[res] * POTENTIAL_AVAILABILITY / 100

# Renewable energy potential (Resource volume)
potential_BIOMASS_data = pd.read_csv('input/potential/renewables_potential_MWh_base.csv', index_col='code', dtype={'code':str})
potential_BIOMASS = city_to_substation(potential_BIOMASS_data)

# Region matrix
matrix = pd.read_csv(f'input/grid_matrix_{NETWORK}.csv', index_col='code', dtype={'code':str}) # Adjacency matrix
matrix = matrix.loc[REGION,REGION]
distance = pd.read_csv('input/grid_matrix_km.csv', index_col='code', dtype={'code':str})
grid_cap_exist = pd.read_csv(f'input/grid_matrix_MW.csv', index_col='code', dtype={'code':str})
if YEAR > 2020:
    prev_result = get_model_name(year=YEAR-10)
    if os.path.isfile(f'output/{prev_result}/grid_{YEAR-10}.csv'):
        grid_cap_exist = pd.read_csv(f'output/{prev_result}/grid_{YEAR-10}.csv', index_col='code', dtype={'code':str})
else:
    # Additional lines
    NEWLINE = [('12351','52019'),('52019','152056'),('141305','122297'),('234451','232319')]
    # Remove from current network
    for r0,r1 in NEWLINE:
        matrix.loc[(r0,r1)] = 0
        matrix.loc[(r1,r0)] = 0

# Neighbor list
NEIGHBOR = {}
for r in REGION:
    NEIGHBOR[r] = matrix[r][matrix[r] == 1].index.to_list()
        
# AC transmission
grid_loss = distance / 100 * 0.007 # 0.7% losses per 100km
grid_cost = distance * P['fixed_cost']['LVAC']
# High-voltage transmission (Onshore/offshore and HVAC/HVDC)
HVDC = pd.read_csv('input/transmission_lines_HVDC.csv', index_col=['start_region', 'end_region'], dtype={'start_region':str, 'end_region':str})
HVAC = pd.read_csv('input/transmission_lines_HVAC.csv', index_col=['start_region', 'end_region'], dtype={'start_region':str, 'end_region':str})
for line in HVDC.index:
    grid_cost.loc[line[0],line[1]] = round(distance[line[0]][line[1]] * HVDC['cable_cost'][line] + HVDC['converter_cost'][line],2)
    grid_cost.loc[line[1],line[0]] = round(distance[line[1]][line[0]] * HVDC['cable_cost'][line] + HVDC['converter_cost'][line],2)
    grid_loss.loc[line[0],line[1]] = distance[line[0]][line[1]] / 100 * 0.003 + 0.01 # 0.3% losses per 100km for DC + 1% of conversion loss by VSC
    grid_loss.loc[line[1],line[0]] = distance[line[1]][line[0]] / 100 * 0.003 + 0.01
for line in HVAC.index:
    if line not in HVDC.index:
        grid_cost.loc[line[0],line[1]] = distance[line[0]][line[1]] * P['fixed_cost']['HVAC']
        grid_cost.loc[line[1],line[0]] = distance[line[1]][line[0]] * P['fixed_cost']['HVAC']

# H2 demand
h2_demand = pd.read_csv('input/h2_demand.csv', index_col=0, dtype={'code':str})
h2_demand['scenario'] = h2_demand['weight'] * scenario['Final Energy|Hydrogen'][str(YEAR)] * 1000000 # TWh -> MWh
SPREGION['h2'] = h2_demand.index.to_list()
SPREGION['h2'] = [r for r in SPREGION['h2'] if r in SUBSTATION]
h2 = pd.DataFrame(index=TIME, columns=SPREGION['h2'])
for r in SPREGION['h2']:
    h2[r] = [round(h2_demand['scenario'][r] / T_LEN, 1) for t in TIME]

# Generation capacity
#  Esisting capacity (1960-2020)
if YEAR < 2040 or NUCLEAR_AVAILABILITY == 2:
    capacity_data = pd.read_csv('input/power_plant_woNewNuclear.csv', dtype={'node':str})
else:
    capacity_data = pd.read_csv('input/power_plant.csv', dtype={'node':str})

#  Empty capacity
capacity_data_empty = pd.DataFrame(
    [[c1, c2, c3, 0] 
      for c1 in REGION
      for c2 in THERMAL+RESOURCE+WOODY+WASTE+STORAGE+H2TECH+DACCS+AUX
      for c3 in [1960,1970,1980,1990,2000,2010,2020,2030,2040,2050]],
    columns=['node', 'tech', 'year', 'MW'])

#  Calculated capacity from previous step
for year in [2020,2030,2040,2050]:
    if year < YEAR:
        prev_result = get_model_name(year=year)
        if os.path.isfile(f'output/{prev_result}/capacity_added_{year}.csv'):
            prev_result_capacity = pd.read_csv(f'output/{prev_result}/capacity_added_{year}.csv', dtype={'node':str})
            capacity_data = pd.concat([capacity_data, prev_result_capacity], axis=0)

#  Active capacity in target year
capacity_data = pd.concat([capacity_data, capacity_data_empty], axis=0).groupby(['node','tech','year']).sum()['MW'].reset_index()
capacity_data['expiration_year'] = capacity_data['year'] + capacity_data['tech'].map(P['lifetime']) # Final operation year

if YEAR >= 2030:
    capacity_data['active_capacity'] = capacity_data.apply(lambda row: row['MW'] if (row['year'] <= YEAR) & (row['expiration_year'] >= YEAR) else 0, axis=1) # Exclude expired or planned facilities
else:
    capacity_data['active_capacity'] = capacity_data.apply(lambda row: row['MW'] if row['year'] <= YEAR else 0, axis=1) # Utilize all existing facilities in 2020

#  Total active capacity
capacity_active = capacity_data.groupby(['node', 'tech'])['active_capacity'].sum().unstack(fill_value=0)
capacity_exist = capacity_data.groupby(['node', 'tech'])['MW'].sum().unstack(fill_value=0) # Including retired capacity

# Power plant node list
SPREGION['gas-p'] = capacity_exist[(capacity_exist['gas-p'] > 0) | (capacity_exist['gas-c'] > 0)].index.to_list() # Replaceable
SPREGION['gas-c'] = capacity_exist[(capacity_exist['gas-p'] > 0) | (capacity_exist['gas-c'] > 0)].index.to_list() # Replaceable
SPREGION['coalp'] = capacity_active[(capacity_active['coalp'] > 0) | (capacity_active['coalc'] > 0)].index.to_list() # To be phase out
SPREGION['coalc'] = capacity_active[(capacity_active['coalp'] > 0) | (capacity_active['coalc'] > 0)].index.to_list() # To be phase out
SPREGION['woody'] = capacity_exist[(capacity_exist['woody'] > 0) | (capacity_exist['beccs'] > 0)].index.to_list() # Replaceable
SPREGION['beccs'] = capacity_exist[(capacity_exist['woody'] > 0) | (capacity_exist['beccs'] > 0)].index.to_list() # Replaceable
SPREGION['oil-p'] = capacity_exist[capacity_exist['oil-p'] > 0].index.to_list() # Replaceable
SPREGION['nuclr'] = capacity_active[capacity_active['nuclr'] > 0].index.to_list() # Exogenous
SPREGION['waste'] = SUBSTATION
SPREGION['msw-c'] = SUBSTATION

# Power plant node dictionary
PLANT = {}
for r in REGION:
    PLANT[r] = [tech for tech in THERMAL+WOODY+WASTE if r in SPREGION[tech]]
for r in SPREGION['h2']:
    PLANT[r].append('h2-el')


# Technical potential -> Developable potential
for res in ['geoth','river']:
    potential_VRE[res] = potential_VRE[res] * 0.5


########### Dicision variables ##########

cap = {} # capacity
gen = {} # generation
exp = {} # export
imp = {} # import
chg = {} # charge
dcg = {} # discharge
soc = {} # state of charge
crt = {} # curtailment
grd = {} # grid capacity
prd = {} # H2 production
hcg = {} # H2 charge
hdg = {} # H2 discharge
hsc = {} # H2 state of charge
ih2 = {} # Imported H2 supply
dac = {} # DACCS
dammy04 = 'xxxx'
dammy06 = 'xxxxxx'

for r in tqdm(REGION):
    cap[r] = {}
    exp[r] = {}
    imp[r] = {}
    crt[r] = {}
    grd[r] = {}
    for res in RESOURCE:
        cap[r][res] = model.addVar(vtype="C", name="cap_%06s__%s_%04s" % (REGION06[r],res,dammy04))
    for to in NEIGHBOR[r]:
        grd[r][to] = model.addVar(vtype="C", name="grd_%06s_%06s_%04s" % (REGION06[r],REGION06[to],dammy04))
    for t in TIME:
        exp[r][t] = {}
        imp[r][t] = {}
        crt[r][t] = model.addVar(vtype="C", name="crt_%06s_%06s_%04d" % (REGION06[r],dammy06,t))
        for to_from in NEIGHBOR[r]:
            exp[r][t][to_from] = model.addVar(vtype="C", name="exp_%06s_%06s_%04d" % (REGION06[r],REGION06[to_from],t))
            imp[r][t][to_from] = model.addVar(vtype="C", name="imp_%06s_%06s_%04d" % (REGION06[r],REGION06[to_from],t))

for r in tqdm(SUBSTATION):
    chg[r] = {}
    dcg[r] = {}
    soc[r] = {}
    gen[r] = {}
    for fuel in THERMAL+WOODY:
        if r in SPREGION[fuel]:
            cap[r][fuel] = model.addVar(vtype="C", name="cap_%06s__%s_%04s" % (REGION06[r],fuel,dammy04))
    for res in STORAGE + ['stpcs'] + WASTE:
        cap[r][res] = model.addVar(vtype="C", name="cap_%06s__%s_%04s" % (REGION06[r],res,dammy04))
    for t in TIME:
        soc[r][t] = {}
        chg[r][t] = {}
        dcg[r][t] = {}
        gen[r][t] = {}
        for st in STORAGE:
            soc[r][t][st] = model.addVar(vtype="C", name="str_%06s__%s_%04d" % (REGION06[r],st,t))
            chg[r][t][st] = model.addVar(vtype="C", name="chg_%06s__%s_%04d" % (REGION06[r],st,t))
            dcg[r][t][st] = model.addVar(vtype="C", name="dcg_%06s__%s_%04d" % (REGION06[r],st,t))
        for bio in WASTE:
            gen[r][t][bio] = model.addVar(vtype="C", name="gen_%06s__%s_%04d" % (REGION06[r],bio,t))
        for fuel in THERMAL+WOODY:
            if r in SPREGION[fuel]:
                gen[r][t][fuel] = model.addVar(vtype="C", name="gen_%06s__%s_%04d" % (REGION06[r],fuel,t))

for r in tqdm(SPREGION['h2']):
    prd[r] = {}
    hcg[r] = {}
    hdg[r] = {}
    hsc[r] = {}
    ih2[r] = {}
    for t in TIME:
        gen[r][t]['h2-el'] = model.addVar(vtype="C", name="gen_%06s__h2-el_%04d" % (REGION06[r],t))
        prd[r][t] = model.addVar(vtype="C", name="prd_%06s__el-h2_%04d" % (REGION06[r],t))
        hcg[r][t] = model.addVar(vtype="C", name="hcg_%06s_%06s_%04d" % (REGION06[r],dammy06,t))
        hdg[r][t] = model.addVar(vtype="C", name="hdg_%06s_%06s_%04d" % (REGION06[r],dammy06,t))
        hsc[r][t] = model.addVar(vtype="C", name="hsc_%06s_%06s_%04d" % (REGION06[r],dammy06,t))
        ih2[r][t] = model.addVar(vtype="C", name="ih2_%06s_%06s_%04d" % (REGION06[r],dammy06,t))
    for tech in H2TECH + ['h2cmp']:
        cap[r][tech] = model.addVar(vtype="C", name="cap_%06s__%s_%04s" % (REGION06[r],tech,dammy04))

for r in tqdm(SPREGION['ccs']):
    dac[r] = {}
    for tech in DACCS:
        cap[r][tech] = model.addVar(vtype="C", name="cap_%06s__%s_%04s" % (REGION06[r],tech,dammy04))
    for t in TIME:
        dac[r][t] = model.addVar(vtype="C", name="dac_%06s_%06s_%04d" % (REGION06[r],dammy06,t))


model.update()


########### Constraints ##########

# Substation nodes
for r in tqdm(SUBSTATION): 

    # Technology availability
    DISPATCH = PLANT[r]
    
    # Electricity balance    
    for n, t in enumerate(TIME):
        # Supply = Demand 
        model.addConstr(gp.quicksum(cap[r][res] * profile[res][r][t] for res in RESOURCE) 
        + gp.quicksum(gen[r][t][fuel] for fuel in DISPATCH)
        + gp.quicksum(imp[r][t][frm] for frm in NEIGHBOR[r])
        + gp.quicksum(dcg[r][t][st] for st in STORAGE)
        == regional_future_demand[r][t] + crt[r][t]
            + gp.quicksum(chg[r][t][st] for st in STORAGE)
            + gp.quicksum(exp[r][t][to] for to in NEIGHBOR[r])
            + (prd[r][t] / P['ef']['el-h2'] if r in SPREGION['h2'] else 0)
            + (dac[r][t] if r in SPREGION['ccs'] else 0), name=f"ele_{REGION06[r]}_tsnode_{TIME04[t]}")
            
        # Storage consistency
        for st in STORAGE:
            model.addConstr(soc[r][t][st] == soc[r][TIME[-1]][st] + chg[r][t][st] * P['ef'][st] - dcg[r][t][st] / P['ef'][st] if t == TIME[0] else soc[r][t][st] == soc[r][TIME[n-1]][st] + chg[r][t][st] * P['ef'][st] - dcg[r][t][st] / P['ef'][st], name=f"soc_{REGION06[r]}__{st}_{TIME04[t]}")
            model.addConstr(dcg[r][t][st] <= soc[r][TIME[-1]][st] * P['ef'][st] if t == TIME[0] else dcg[r][t][st] <= soc[r][TIME[n-1]][st] * P['ef'][st], name=f"dcg_{REGION06[r]}__{st}_{TIME04[t]}")
        model.addConstr(dcg[r][t]['stpmp'] <= cap[r]['stpmp'] / 10, name=f"pdc_{REGION06[r]}__stpmp_{TIME04[t]}") # MW = MWh / 10 (NREL ATB 2023)
        model.addConstr(chg[r][t]['stpmp'] <= cap[r]['stpmp'] / 10, name=f"pch_{REGION06[r]}__stpmp_{TIME04[t]}") # MW = MWh / 10 (NREL ATB 2023)

        # Storage capacity
        model.addConstr(chg[r][t]['stbat'] + dcg[r][t]['stbat'] <= cap[r]['stpcs'] * STEP, name=f"stc_{REGION06[r]}__stpcs_{TIME04[t]}") # Power capacity (MW)
        for st in ['stpmp','stbat']:
            model.addConstr(soc[r][t][st] <= cap[r][st], name=f"str_{REGION06[r]}__{st}_{TIME04[t]}") # Energy capacity (MWh)

        # Generation capacity
        for fuel in [tech for tech in DISPATCH if tech not in ['nuclr']]:
            model.addConstr(gen[r][t][fuel] <= cap[r][fuel] * STEP, name=f"gen_{REGION06[r]}__{fuel}_{TIME04[t]}")

    # Storage limitation
    model.addConstr(cap[r]['stpmp'] == storage['pump_hydro'][r] * 10, name=f"dam_{REGION06[r]}__stpmp_{dammy04}") # Maximum SoC
    
    # New grid capacity >= Active grid capacity
    for neighbor in NEIGHBOR[r]:
        model.addConstr(grd[r][neighbor] >= grid_cap_exist[r][neighbor], name=f"gxc_{REGION06[r]}_{REGION06[neighbor]}_{dammy04}")

# New generation capacity >= Active generation capacity
for r in SPREGION['oil-p']:
    model.addConstr(cap[r]['oil-p'] >= capacity_active['oil-p'][r], name=f"cap_{REGION06[r]}__oil-p_{dammy04}")
    model.addConstr(cap[r]['oil-p'] <= capacity_exist['oil-p'][r], name=f"ucp_{REGION06[r]}__oil-p_{dammy04}")
for r in SPREGION['coalp']:
    model.addConstr(cap[r]['coalp'] + cap[r]['coalc'] >= capacity_active['coalp'][r] + capacity_active['coalc'][r], name=f"cap_{REGION06[r]}__coalp_{dammy04}")
    model.addConstr(cap[r]['coalp'] + cap[r]['coalc'] <= (capacity_exist['coalp'][r] + capacity_exist['coalc'][r]), name=f"ucp_{REGION06[r]}__coalp_{dammy04}")
    model.addConstr(cap[r]['coalc'] >= capacity_active['coalc'][r], name=f"cap_{REGION06[r]}__coalc_{dammy04}")
for r in SPREGION['gas-p']:
    model.addConstr(cap[r]['gas-p'] + cap[r]['gas-c'] >= capacity_active['gas-p'][r] + capacity_active['gas-c'][r], name=f"cap_{REGION06[r]}__gas-p_{dammy04}")
    model.addConstr(cap[r]['gas-p'] + cap[r]['gas-c'] <= (capacity_exist['gas-p'][r] + capacity_exist['gas-c'][r]), name=f"ucp_{REGION06[r]}__gas-p_{dammy04}")
    model.addConstr(cap[r]['gas-c'] >= capacity_active['gas-c'][r], name=f"cap_{REGION06[r]}__gas-c_{dammy04}")
for r in SPREGION['woody']:
    model.addConstr(cap[r]['woody'] + cap[r]['beccs'] >= capacity_active['woody'][r] + capacity_active['beccs'][r], name=f"cap_{REGION06[r]}__woody_{dammy04}")
    model.addConstr(cap[r]['beccs'] >= capacity_active['beccs'][r], name=f"cap_{REGION06[r]}__beccs_{dammy04}")
for r in SPREGION['waste']:
    model.addConstr(cap[r]['waste'] + cap[r]['msw-c'] >= capacity_active['waste'][r] + capacity_active['msw-c'][r], name=f"cap_{REGION06[r]}__waste_{dammy04}")
    model.addConstr(cap[r]['msw-c'] >= capacity_active['msw-c'][r], name=f"cap_{REGION06[r]}__msw-c_{dammy04}")
    model.addConstr(gp.quicksum(gen[r][t][tech] / P['ef'][tech] for tech in WASTE for t in TIME) <= potential_BIOMASS['waste'][r] * T_SCALE, name=f"res_{REGION06[r]}__waste_{dammy04}")

# Woody biomass potential (National cap)
model.addConstr(gp.quicksum(gen[r][t][tech] / P['ef'][tech] for tech in WOODY for t in TIME for r in SPREGION['woody']) <= potential_BIOMASS['woody'].sum().round(-5) * BIOMASS_CAP * T_SCALE, name=f"res_{REGION06[r]}__{'woody'}_{dammy04}")

# Nuclear power capacity (Fixed)
if NUCLEAR_AVAILABILITY != 0:
    for r in SPREGION['nuclr']:
        model.addConstr(cap[r]['nuclr'] == capacity_active['nuclr'][r], name=f"cap_{REGION06[r]}__nuclr_{dammy04}")
        for t in TIME:
            model.addConstr(gen[r][t]['nuclr'] == capacity_active['nuclr'][r] * STEP * P['cf']['nuclr'], name=f"gen_{REGION06[r]}__nuclr_{TIME04[t]}")

# Electricity balance in terminal nodes
for r in tqdm(NODE):
    for t in TIME:
        model.addConstr(gp.quicksum(cap[r][res] * profile[res][r][t] for res in RESOURCE)
        + gp.quicksum(imp[r][t][frm] for frm in NEIGHBOR[r])
        == regional_future_demand[r][t] + crt[r][t] 
            + gp.quicksum(exp[r][t][to] for to in NEIGHBOR[r]), name=f"ele_{REGION06[r]}_dsnode_{TIME04[t]}")
    
# All nodes
for r in tqdm(REGION):
    
    for t in TIME:
        # Curtailment
        model.addConstr(crt[r][t] <= gp.quicksum(cap[r][res] * profile[res][r][t] for res in RESOURCE), name=f"crt_{REGION06[r]}_{dammy06}_{TIME04[t]}")

        # Transmission
        for neighbor in NEIGHBOR[r]:
            # Import = Export
            model.addConstr(exp[r][t][neighbor] * (1-grid_loss[r][neighbor]) == imp[neighbor][t][r], name=f"trd_{REGION06[r]}_{REGION06[neighbor]}_{TIME04[t]}")
            # Capacity
            model.addConstr(grd[r][neighbor] == grd[neighbor][r], name=f"grd_{REGION06[r]}_{REGION06[neighbor]}_{TIME04[t]}")
            model.addConstr(exp[r][t][neighbor] <= grd[r][neighbor] * STEP, name=f"exp_{REGION06[r]}_{REGION06[neighbor]}_{TIME04[t]}")

    # Renewables
    for res in [res for res in RESOURCE if res not in ['hydro']]:
        # Resource limitation
        model.addConstr(cap[r][res] * CF_annual[res][r] * 8760 <= max(potential_VRE[res][r], capacity_active[res][r] * CF_annual[res][r] * 8760), name=f"res_{REGION06[r]}__{res}_{dammy04}")
        # Existing capacity
        model.addConstr(cap[r][res] >= capacity_active[res][r], name=f"cap_{REGION06[r]}__{res}_{dammy04}")
    
    # Existing capacity
    model.addConstr(cap[r]['hydro'] == capacity_active['hydro'][r], name=f"cph_{REGION06[r]}__hydro_{dammy04}")

# H2 nodes
for r in tqdm(SPREGION['h2']):
    for n, t in enumerate(TIME):
        # H2 supply = H2 demand
        model.addConstr(prd[r][t] + hdg[r][t] == h2[r][t] + hcg[r][t] + (gen[r][t]['h2-el'] / P['ef']['h2-el']), name=f"hyd_{REGION06[r]}_{dammy06}_{TIME04[t]}")
        # H2 storage
        model.addConstr(hsc[r][t] == hsc[r][TIME[-1]] + ih2[r][t] + hcg[r][t] * P['ef']['st-h2'] - hdg[r][t] / P['ef']['st-h2'] if t == TIME[0] else hsc[r][t] == hsc[r][TIME[n-1]] + ih2[r][t] + hcg[r][t] * P['ef']['st-h2'] - hdg[r][t] / P['ef']['st-h2'], name=f"soc_{REGION06[r]}__st-h2_{TIME04[t]}")
        model.addConstr(hdg[r][t] <= hsc[r][TIME[-1]] * P['ef']['st-h2'] if t == TIME[0] else hdg[r][t] <= hsc[r][TIME[n-1]] * P['ef']['st-h2'], name=f"dcg_{REGION06[r]}__st-h2_{TIME04[t]}")
        # H2 capacity
        model.addConstr(prd[r][t] <= cap[r]['el-h2'] * STEP, name=f"cap_{REGION06[r]}__el-h2_{TIME04[t]}")
        model.addConstr(hcg[r][t] + hdg[r][t] <= cap[r]['h2cmp'] * STEP, name=f"cap_{REGION06[r]}__h2cmp_{TIME04[t]}")
        model.addConstr(hsc[r][t] <= cap[r]['st-h2'], name=f"cap_{REGION06[r]}__st-h2_{TIME04[t]}")
    # Existing capacity
    for tech in H2TECH+['h2cmp']:
        model.addConstr(cap[r][tech] >= capacity_active[tech][r], name=f"cap_{REGION06[r]}__{res}_{dammy04}")

# CCS nodes
for r in tqdm(SPREGION['ccs']):
    # CCS limit
    model.addConstr(gp.quicksum(dac[r][t] for t in TIME) * P['cdr']['daccs'] <= ccs_potential[r], name=f"dac_{REGION06[r]}_{dammy06}_{dammy04}")
    for t in TIME:
        model.addConstr(dac[r][t] <= cap[r]['daccs'] * STEP, name=f"cap_{REGION06[r]}__daccs_{TIME04[t]}")
    # Existing capacity
    model.addConstr(cap[r]['daccs'] >= capacity_active['daccs'][r], name=f"cap_{REGION06[r]}__daccs_{dammy04}")

# Generation reserve
GENERATION_RESERVE = 0.1 # 10%
for t in TIME:
    model.addConstr(gp.quicksum(cap[r][fuel] * STEP - gen[r][t][fuel] for r in SUBSTATION for fuel in PLANT[r]) 
                    + gp.quicksum(soc[r][t][tech] * P['ef'][tech] for tech in STORAGE for r in SUBSTATION) 
                    >= regional_future_demand.T.sum()[t] * GENERATION_RESERVE, name=f"srv_{dammy06}_{dammy06}_{TIME04[t]}")

# CO2 emissions
model.addConstr(gp.quicksum(gen[r][t][fuel] / P['ef'][fuel] * P['cef'][fuel] for t in TIME for r in SUBSTATION  for fuel in THERMAL if r in SPREGION[fuel])
                + gp.quicksum(gen[r][t][fuel] / P['ef'][fuel] * P['cef'][fuel] for t in TIME for r in SUBSTATION  for fuel in WASTE)
                - gp.quicksum(gen[r][t][fuel] / P['ef'][fuel] * P['cdr'][fuel] for t in TIME for r in SPREGION['woody'] for fuel in WOODY)
                - gp.quicksum(dac[r][t] * P['cdr']['daccs'] for t in TIME for r in SPREGION['ccs']) <= co2_cap * T_SCALE, name=f"co2_{dammy06}_{dammy06}_{dammy04}")

# CCS limits
if CCS_AVAILAVILITY != 1:
    CCS_TECH_DICT = {'gas-c':'gas-p','coalc':'coalp'}
    ccs_cap = ccs_potential.sum() if CCS_AVAILAVILITY == 2 else 0
    model.addConstr(gp.quicksum(gen[r][t][fuel] / P['ef'][fuel] * (P['cef'][CCS_TECH_DICT[fuel]] - P['cef'][fuel]) for t in TIME for r in SUBSTATION for fuel in ['gas-c','coalc'] if r in SPREGION[fuel])
                    + gp.quicksum(gen[r][t][fuel] / P['ef'][fuel] * P['cdr'][fuel] for t in TIME for r in SPREGION['woody'] for fuel in ['beccs'])
                    + gp.quicksum(dac[r][t] * P['cdr']['daccs'] for t in TIME for r in SPREGION['ccs']) <= ccs_cap * T_SCALE, name=f"ccs_{dammy06}_{dammy06}_{dammy04}")


########### Objective function ##########
model.update()

model.setObjective(gp.quicksum(cap[r][tech] * P['fixed_cost'][tech] for r in REGION for tech in RESOURCE)
+ gp.quicksum(cap[r][tech] * P['fixed_cost'][tech] for r in SUBSTATION for tech in STORAGE + ['stpcs'])
+ gp.quicksum(cap[r][tech] * P['fixed_cost'][tech] for r in SPREGION['h2'] for tech in H2TECH + ['h2cmp'])
+ gp.quicksum(cap[r][tech] * P['fixed_cost'][tech] for r in SPREGION['ccs'] for tech in DACCS)
+ gp.quicksum((cap[r][tech] * P['fixed_cost'][tech] if r in SPREGION[tech] else 0) for r in SUBSTATION for tech in THERMAL + WOODY + WASTE)
+ gp.quicksum(ih2[r][t] * P['variable_cost']['ih2-f'] for r in SPREGION['h2'] for t in TIME) * T_EXPAND
+ gp.quicksum(dac[r][t] * P['variable_cost']['daccs'] for r in SPREGION['ccs'] for t in TIME) * T_EXPAND
+ gp.quicksum((gen[r][t][fuel] * P['variable_cost'][fuel] if r in SPREGION[fuel] else 0) for r in SUBSTATION for t in TIME for fuel in THERMAL + WOODY + WASTE) * T_EXPAND
+ gp.quicksum(grd[r][to] * grid_cost[r][to] for r in REGION for to in NEIGHBOR[r])
+ gp.quicksum((chg[r][t][st] + dcg[r][t][st]) * 0.00001 for r in SUBSTATION for t in TIME for st in STORAGE) * T_EXPAND
+ gp.quicksum((exp[r][t][to] + imp[to][t][r]) * 0.00001 for r in REGION for to in NEIGHBOR[r] for t in TIME) * T_EXPAND
+ gp.quicksum((hcg[r][t] + hdg[r][t] + prd[r][t]) * 0.00001 for r in SPREGION['h2'] for t in TIME) * T_EXPAND, GRB.MINIMIZE)


########### Run optimization ##########
print(model_name)
# model.write("output/%s/%s.lp" % (model_name, model.ModelName))

model.optimize()

print(model.objVal/1000000, 'trillion JPY')


########### Output results ##########
os.makedirs('output/%s' % model_name, exist_ok=True)

# Objective function value
ov = pd.DataFrame([[model.objVal]])
ov.to_csv(f'output/{model_name}/objective_value.csv', index=False, header=False)

# Primal optimal
with open('output/%s/primal_%s.csv' % (model_name, model.ModelName), 'w', newline="") as f:
    writer = csv.writer(f, delimiter=",")    
    writer.writerow(["name","id","region","general",'time',"value"])
    for v in model.getVars():
        name = v.VarName
        value = v.X
        writer.writerow([name, name[:3], name[4:10], name[11:17], name[18:22], value])

# Dual optimal
with open('output/%s/dual_%s.csv' % (model_name, model.ModelName), 'w', newline="") as f:
    writer = csv.writer(f, delimiter=",")
    writer.writerow(["name","id","region","general",'time',"value"])
    for cons in model.getConstrs():
        name = cons.ConstrName
        value = cons.Pi
        writer.writerow([name, name[:3], name[4:10], name[11:17], name[18:22], value])

# All variables
optimal = pd.read_csv('output/%s/primal_%s.csv' % (model_name,model_name), index_col=0, dtype={'region':str, 'time':str})
optimal = optimal.replace('_', '', regex=True)
optimal = optimal.replace(' ', '', regex=True)

# Additional capacity
capacity_total = capacity_active.copy()
capacity_region = optimal[optimal.id == 'cap'].groupby(['region','general']).sum()['value'].astype(float)

for tech in THERMAL+RESOURCE+WOODY+WASTE+STORAGE+H2TECH+DACCS+AUX:
    try:
        capacity_total[tech] = capacity_region.unstack()[tech].loc[REGION].fillna(0)
    except:
        capacity_total[tech] = [0 for i in REGION]
capacity_added = capacity_total - capacity_active
capacity_added = capacity_added.stack().reset_index()
capacity_added.columns = ['node','tech','MW']
capacity_added['year'] = YEAR
capacity_added.to_csv(f'output/{model_name}/capacity_added_{YEAR}.csv', index=False)

# Cumulative capacity
capacity_region = capacity_region.reset_index()
capacity_region.columns = ['node','tech','MW']
capacity_region['year'] = YEAR
capacity_region.to_csv(f'output/{model_name}/capacity_total_{YEAR}.csv', index=False)

# New grid capacity
grid = optimal[optimal.id == 'grd'].groupby(['region','general'], as_index=True).sum()['value'].astype(float)
grid_cap_exist.astype(float).update(grid.unstack())
grid_cap_exist.to_csv(f'output/{model_name}/grid_{YEAR}.csv')