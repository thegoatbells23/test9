#!/usr/bin/env python3
"""
Load a county CSV such as raw_data/county_pops2.csv into the counties
collection in MongoDB, replacing whatever is there.
The file is tab-separated with no header row. Its columns are:
county name, state code, population (with commas), area in square
miles, and metro area (may be empty).
"""

import csv
import sys

import data.db_connect as dbc
from counties.fields import (
    AREA,
    METRO_AREA,
    NAME,
    POPULATION,
    STATE_CODE,
)
from counties.query import COUNTIES_COLLECT

CSV_COLS = (NAME, STATE_CODE, POPULATION, AREA, METRO_AREA)


def load_counties(file_path: str) -> list:
    """
    Read the county file and return its rows as lists of strings.
    """
    with open(file_path, mode='r', newline='') as csvfile:
        return [row for row in csv.reader(csvfile, delimiter='\t') if row]


def row_to_county(row: list) -> dict:
    """
    Convert one row of the file to a county record using our field
    names. Raises ValueError if the row does not have 5 columns or its
    numbers cannot be read.
    """
    if len(row) != len(CSV_COLS):
        raise ValueError(f'Expected {len(CSV_COLS)} columns, got {row}')
    name, state_code, population, area, metro_area = (
        col.strip() for col in row)
    return {
        STATE_CODE: state_code,
        NAME: name,
        POPULATION: int(population.replace(',', '')),
        AREA: float(area),
        METRO_AREA: metro_area,
    }


def store_counties(counties: list, collection=COUNTIES_COLLECT) -> int:
    """
    Replace the contents of the counties collection with `counties`.
    Returns the number of counties stored.
    """
    dbc.drop(collection)
    for county in counties:
        dbc.create(collection, county)
    return len(counties)


def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("USAGE: python load.py <path_to_county_file>")
        sys.exit(1)

    counties = [row_to_county(row) for row in load_counties(file_path)]
    count = store_counties(counties)
    print(f"Stored {count} counties in {dbc.SE_DB}.{COUNTIES_COLLECT}.")


if __name__ == "__main__":
    main()
