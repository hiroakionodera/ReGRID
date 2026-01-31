#!/bin/bash
pathway='C1'
tech='ccs-biomass'
case='base'
for year in 2020 2030 2040 2050; do
    python model.py $pathway $year $tech $case
done