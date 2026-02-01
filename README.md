# ReGRID Model

### Energy System Optimization Model for Regional Grid Integration and Decarbonization

Key features
- Simultaneously optimizes regional capacity planning and spatio-temporal operation for:
  Power generation, Energy storage, Transmission networks, Hydrogen technologies, Carbon removal technologies.
- Can be soft-linked with integrated assessment models (IAMs) to design energy systems aligned with diverse socioeconomic and emissions pathways.
- Cost-minimization based on linear programming.
- Covers all 1,741 municipalities across Japan.

Model description is provided in [Wiki](https://github.com/hiroakionodera/ReGRID/wiki).

<br>

# Applications
| Directory | Publication | Key extension |
|---------|------------|---------------|
| DataCenter | Strategic data center siting can mitigate dilemmas between digitalization and decarbonization (Under review) | Endogenizes the spatial siting of electricity-intensive end users within the energy transition. Quantifies marginal grid costs of end users. |
| Conservation | Spatial strategies for reconciling area-based conservation and renewable energy transition in Japan. (In preparation) | Optimizes renewable energy deployment under area-based conservation constraints. |

<br>

# Requirements

- Python 3.8+
- `gurobipy`: To solve optimization problem (Tested on version 12.0)
- `pandas`, `numpy`, `tqdm`: For data handling and managing processing

<br>

# How to Run
1. Prepare input CSV files under the input/ directory.
2. Execute model.py.
   It should be executed recursively every 10 years (2020, 2030, 2040, and 2050).

Note:
- Full-scale optimization (1,741 nodes, 6-hourly resolution for one year) requires approximately 10–50 hours (using Intel Core-i9 14900KS).
- At least 80 GB of RAM is recommended for stable execution.
- model.py outputs:
  - Primal optimal solutions (1~3 GB)
  - Dual optimal solutions (1~3 GB)

<br>

# Publications
1. Hiroaki Onodera et al.; 2024. The role of regional renewable energy integration in electricity decarbonization—A case study of Japan. Applied Energy.
[https://doi.org/10.1016/j.apenergy.2024.123118](https://doi.org/10.1016/j.apenergy.2024.123118) (Original version)
2. Hiroaki Onodera et al.; Strategic data center siting can mitigate dilemmas between digitalization and decarbonization. Preprint. [https://www.researchsquare.com/article/rs-6707312/v2](https://www.researchsquare.com/article/rs-6707312/v2)
3. Hiroaki Onodera et al.; Spatial strategies for reconciling area-based conservation and renewable energy transition in Japan. (In preparation)
