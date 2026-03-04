# Spatial strategies for reconciling area-based conservation and renewable energy transition in Japan

<br>

# Structure
| File              | Description | Depends on |
|-------------------|-------------|-------------|
| `model.py`       | Optimizes energy system snapshots for the target year.|-|
| `model_run.sh`       | Runs `model.py`  in a loop for multiple years or scenarios. |-|
| `analysis_system.ipynb`       | Analyzes system configurations.|`model.py`|
| `analysis_grid.ipynb`       | Visualizes power grid maps.|`model.py`|
| `analysis_capacity.ipynb`       | Analyzes capacity and operations of technologies.|`model.py`|
| `analysis_LMP.ipynb`       | Analyzes locational marginal prices and visualizes them on a map.|`model.py`|
| `analysis_MOC.ipynb`       | Analyzes marginal value of regional renewable energy and marginal opportunity cost of area-based conservation and visualizes them on a map.|`model.py`|
| `analysis_transition.ipynb`       | Visualizes transition pathways over time.|`model.py`, `analysis_system.ipynb`|
| `analysis_scenarios.ipynb`       | Compares results across different scenarios.|`model.py`, `analysis_system.ipynb`|
| `analysis_potential.ipynb`       | Compares results from renewable energy potential assessmant.|-|
| `analysis_map.ipynb`       | Visualizes municipal-level maps.|-|
| `analysis_renewables_area.ipynb`       | Visualizes spacing area of renewables and overlap with PCAs.|`model.py`|

<br>

# Data repository
Input data and results presented in the paper are available at:
https://zonode.org/records/xxxxxxxx (to be available after paper publication).

<br>

# Model features

## Renewable energy deployment constraints

Installed capacity of solar PV, onshore wind, floating offshore wind, fixed-bottom offshore wind are capped by technical potential ($p_{r,g}$) based on spatial assessment considering area-based conservation.

$$
W_{r,g} \leq p_{r,g}
$$

(Full model description is available at [Wiki](https://github.com/hiroakionodera/ReGRID/wiki).)
