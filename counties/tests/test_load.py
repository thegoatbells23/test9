import os
from unittest.mock import patch

import pytest

import counties.fields as flds
import counties.load as ld

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'raw_data',
                        'county_pops2.csv')

TEST_ROW = ['Autauga', ' AL', '58,805', '594.44',
            'Montgomery, AL Metropolitan Statistical Area']


def test_load_counties():
    rows = ld.load_counties(CSV_PATH)
    assert len(rows) > 0
    for row in rows:
        assert len(row) == len(ld.CSV_COLS)


def test_row_to_county():
    assert ld.row_to_county(TEST_ROW) == {
        flds.STATE_CODE: 'AL',
        flds.NAME: 'Autauga',
        flds.POPULATION: 58805,
        flds.AREA: 594.44,
        flds.METRO_AREA: 'Montgomery, AL Metropolitan Statistical Area',
    }


def test_row_to_county_no_metro_area():
    county = ld.row_to_county(TEST_ROW[:-1] + [''])
    assert county[flds.METRO_AREA] == ''


def test_row_to_county_wrong_column_count():
    with pytest.raises(ValueError):
        ld.row_to_county(TEST_ROW[:-1])


def test_row_to_county_bad_population():
    with pytest.raises(ValueError):
        ld.row_to_county(['Autauga', 'AL', 'many', '594.44', ''])


def test_every_row_converts():
    counties = [ld.row_to_county(row) for row in ld.load_counties(CSV_PATH)]
    for county in counties:
        assert len(county[flds.STATE_CODE]) == flds.STATE_CODE_LEN
        assert county[flds.POPULATION] >= 0
        assert county[flds.AREA] >= 0
    keys = [(c[flds.STATE_CODE], c[flds.NAME]) for c in counties]
    assert len(keys) == len(set(keys))  # no county appears twice


@patch('data.db_connect.create', autospec=True)
@patch('data.db_connect.drop', autospec=True)
def test_store_counties(mock_drop, mock_create):
    counties = [ld.row_to_county(TEST_ROW)] * 2
    assert ld.store_counties(counties) == len(counties)
    mock_drop.assert_called_once_with(ld.COUNTIES_COLLECT)
    assert mock_create.call_count == len(counties)


@patch('counties.load.store_counties', autospec=True, return_value=67)
def test_main(mock_store, capsys):
    with patch.object(ld.sys, 'argv', ['load.py', CSV_PATH]):
        ld.main()
    assert '67 counties' in capsys.readouterr().out


def test_main_no_args():
    with patch.object(ld.sys, 'argv', ['load.py']):
        with pytest.raises(SystemExit):
            ld.main()
