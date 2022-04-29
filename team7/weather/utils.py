import pandas as pd
import numpy as np
import requests
import json
import datetime

import weather.models


class LocationAPI:
    isInit = False


def get_location(fips):
    coordinate = weather.models.Coordinate.objects.filter(fips=fips).first()
    if coordinate is None:
        return []
    return [coordinate.latitude, coordinate.longitude]


def get_latest_data(fips, latitude, longitude):
    parameters = "T2M,PRECTOTCORR,GWETTOP,GWETROOT,GWETPROF"  # can choose up to 20 parameters, see google doc
    community = "AG"  # Agroclimatology
    start = "20211201"
    end = "20220101"  # lastest date for soil data
    format = 'JSON'
    request_url = 'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=' \
                  '{0}&community={1}&longitude={2}&latitude={3}&start={4}&end={5}&format={6}'.format(parameters,
                                                                                                     community,
                                                                                                     longitude,
                                                                                                     latitude,
                                                                                                     start,
                                                                                                     end,
                                                                                                     format)
    response = requests.get(request_url)
    api_dict = json.loads(response.text)
    table = pd.DataFrame.from_dict(api_dict['properties']['parameter']).reset_index().rename(columns={"index": "Date",
                                                                                                      "T2M": "Temperature",
                                                                                                      "PRECTOTCORR": "Precipitation",
                                                                                                      "GWETTOP": "Surface Soil Wetness",
                                                                                                      "GWETROOT": "Root Zone Soil Wetness",
                                                                                                      "GWETPROF": "Profile Soil Moisture"})
    num_column = table.T.shape[1]
    table.drop(columns=['Date'], axis=1, inplace=True)
    group = table.T.groupby([[i // 7 for i in range(0, num_column)]], axis=1).mean().T

    date_range = pd.period_range(start='2021-12-01', end='2022-01-01', freq='7D').map(str).str.split('/').str[0]
    date_range = pd.Series(date_range)
    weather = group.assign(Weeks=date_range)
    weather['FIPS'] = fips
    result_df = weather.iloc[len(weather) - 1: len(weather)]

    parameters = "T2M,PRECTOTCORR"  # can choose up to 20 parameters, see google doc
    community = "AG"  # Agroclimatology
    start = "20220101"
    end = get_end_date()  # lastest date for soil data
    format = 'JSON'
    request_url = 'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=' \
    '{0}&community={1}&longitude={2}&latitude={3}&start={4}&end={5}&format={6}'.format(parameters,
                                                                                       community,
                                                                                       longitude,
                                                                                       latitude,
                                                                                       start,
                                                                                       end,
                                                                                       format)

    response = requests.get(request_url)
    api_dict = json.loads(response.text)
    table = pd.DataFrame.from_dict(api_dict['properties']['parameter']).reset_index().rename(columns={"index": "Date",
                                                                                                      "T2M": "Temperature",
                                                                                                      "PRECTOTCORR": "Precipitation"})
    num_column = table.T.shape[1]
    table.drop(columns=['Date'], axis=1, inplace=True)
    group = table.T.groupby([[i // 7 for i in range(0, num_column)]], axis=1).mean().T

    date_range = pd.period_range(start=start, end=end, freq='7D').map(str).str.split('/').str[0]
    date_range = pd.Series(date_range)
    weather = group.assign(Weeks=date_range)
    weather['FIPS'] = fips
    latest_df = weather.iloc[len(weather) - 1: len(weather)]
    print(result_df["Surface Soil Wetness"].iloc[0])
    latest_df["Surface Soil Wetness"] = result_df["Surface Soil Wetness"].iloc[0]
    latest_df["Root Zone Soil Wetness"] = result_df["Root Zone Soil Wetness"].iloc[0]
    latest_df["Profile Soil Moisture"] = result_df["Profile Soil Moisture"].iloc[0]
    return latest_df


def get_end_date():
    cur_datetime = datetime.datetime.now() - datetime.timedelta(4)
    cur_year = str(cur_datetime.year)
    cur_month = str(cur_datetime.month)
    cur_day = str(cur_datetime.day)
    if len(cur_month) < 2:
        cur_month = '0' + cur_month
    if len(cur_day) < 2:
        cur_day = '0' + cur_day
    return cur_year + cur_month + cur_day
