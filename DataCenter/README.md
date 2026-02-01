# Strategic data center siting can mitigate dilemmas between decarbonization and digitalization

<br>

# Structure
| File              | Description | Depends on |
|-------------------|-------------|-------------|
| `model.py`       | Optimizes energy system snapshots for the target year.|-|
| `analysis_system.ipynb`       | Evaluates and visualizes energy system configurations.|`model.py`|
| `analysis_transition.ipynb`       | Visualizes energy system transitions over time.|`model.py`, `analysis_system.ipynb`|
| `analysis_DClocation.ipynb`       | Evaluates the economic impact of data center addition.|`model.py` (Dual variables)|
| `analysis_DCstrategy.ipynb`       | Assesses data center siting strategies.|`model.py`, `analysis_system.ipynb`, `analysis_DClocation.ipynb`|

<br>

# Data repository
Input data are available at:
https://zonode.org/records/xxxxxxxx (to be available after paper publication).

<br>

# Model features

## Electricity balance constraints

Add a new end-user (here, data centers) electricity demand term to the right-hand side. The electricity demand term is given by the product of the decision variable load capacity ($W_r^{\text{DC}}$) and the time-specific static capacity factor ($l'_{r,t}$).

$$
\sum_{g \in \text{VRE}} (h_{r,g,t} \cdot W_{r,g}) +
\sum_{g \in \text{DG}} P_{r,g,t} +
\sum_{r'} T_{r,r',t}^+ +
\sum_{g \in \text{ST}} S_{r,g,t}^- 
= d_{r,t} +
D_{r,t}^{\text{DAC}} +
D_{r,t}^{\text{P2G}} +
\sum_{r'} T_{r,r',t}^- +
\sum_{g \in \text{ST}} S_{r,g,t}^+ +
R_{r,t} +
l'_{r,t} \cdot W_r^{\text{DC}}
\quad \forall r,t
$$

<br>

## Data center siting strategy

For each siting strategy, add constraints that specify the data center load capacity in each node.

**BAU strategy**: Data centers area located according to existing distribution.

$$
W_r^{\text{DC}} = a \cdot \frac{w_r}{\sum_{n \in R}{w_n}}
$$

$a$: Nationwide total capacity of data centers, $w$: Existing capacity of data centers.

**DEV and ILA strategies**: Nationwide total capacity of data centers ($a$) is a given, and the existing capacity is the lower bound of capacity at each regional node.

$$
\sum_{r}{W_r^{\text{DC}}} = a
$$

$$
{W_r^{\text{DC}}} \geqq w_r
$$

**ILA strategy**: The capacity of data centers at each node is capped based on integrated location assessment.

$$
W_r^{\text{DC}} \leqq w_r^{max}
$$

$w_r^{max}$: Maximum capacity of data cneters in node $r$.

(Full model description is available at [Wiki](https://github.com/hiroakionodera/ReGRID/wiki).)