# ReGRID Model

### Energy System Optimization Model for Regional Grid Integration and Decarbonization

Key features
- Covers all 1,741 municipalities across Japan.
- Simultaneously optimizes regional capacity planning and spatio-temporal operation for:
  Power generation, Energy storage, Transmission networks, Hydrogen technologies, Carbon removal technologies.
- Can be soft-linked with integrated assessment models (IAMs) to design energy systems aligned with diverse socioeconomic and emissions pathways.
- Cost-minimization based on linear programming.

Model description is provided in [Wiki](https://github.com/hiroakionodera/ReGRID/wiki).

<br>

# Structure
The model is organized into the following Python modules written in Jupyter Notebook:

| File              | Description | Depends on |
|-------------------|-------------|-------------|
| `model.ipynb`       | Optimizes energy system snapshots for the target year.|-|
| `model_DC.ipynb`       | Customized code of `model.ipynb` for the data center siting strategies.|-|
| `analysis_system.ipynb`       | Evaluates and visualizes energy system configurations.|`model.ipynb`|
| `analysis_transition.ipynb`       | Visualizes energy system transitions over time.|`model.ipynb`, `analysis_system.ipynb`|
| `analysis_DClocation.ipynb`       | Evaluates the economic impact of data center addition.|`model.ipynb` (Dual variables)|
| `analysis_DCstrategy.ipynb`       | Assesses data center siting strategies.|`model.ipynb`, `analysis_system.ipynb`, `analysis_DClocation.ipynb`|

<br>

# Requirements
### Base environment
- Python 3.8+

### Model
- `gurobipy`: To solve optimization problem (Tested on version 12.0)
- `pandas`, `numpy`, `tqdm`: For data handling and managing processing

### Analysis
- `matplotlib`: To draw charts
- `cartopy`: To visualize maps
- `networkx`: To visualize grid networks


<br>

# How to Run
1. Prepare input CSV files under the input/ directory.
2. Execute model.ipynb in a notebook environment (VSCode recommended).
   It should be executed recursively every 10 years (2020, 2030, 2040, and 2050).
3. Run the analysis notebooks according to the dependencies described in **Structure**.

Note:
- Full-scale optimization (1,741 nodes, 6-hourly resolution for one year) requires approximately 10–30 hours, depending on computational resources.
- Example: ~10 hours using Intel Core-i9 14900KS (up to 6.2 GHz).
- At least 80 GB of RAM is recommended for stable execution.
- model.ipynb outputs:
  - Primal optimal solutions (~1 GB)
  - Dual optimal solutions (~1.5 GB)
  (Note: These files are too large to open with standard spreadsheet software such as MS Excel.)
- All results are saved under output/<model_name>/.


<br>

# Publications
1. Hiroaki Onodera et al.; 2024. The role of regional renewable energy integration in electricity decarbonization—A case study of Japan. Applied Energy.
[https://doi.org/10.1016/j.apenergy.2024.123118](https://doi.org/10.1016/j.apenergy.2024.123118) (ReGRID model was originally developed as a part of this research.)
2. Hiroaki Onodera et al.; Strategic data center siting can mitigate dilemmas between digitalization and decarbonization. (In preparation)
