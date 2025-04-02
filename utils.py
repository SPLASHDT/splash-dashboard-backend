import os
from dotenv import load_dotenv
import pandas as pd
from flask import request
from datetime import datetime
import utils
import json


def loadConfigFile():
    """Load environment variables from configuration file
    """

    environment = os.getenv("SPLASH_ENV")

    if environment == "local":
        config_file_path = "config/.env"
    elif environment == "staging":
        config_file_path = "config/.env.staging"
    elif environment == "docker":
        config_file_path = "config/.env.docker"
    else:
        config_file_path = "config/.env.production"

    load_dotenv(config_file_path)


def getLocationDataPaths(option: str):
    """Get datasets paths

    Args:
        option (string): Dataset's name

    Returns:
        Tuple: Absolute paths of wave, wind, Dawlish and Penzance water level folders
    """

    if option == "dawlish" or option == "penzance":
        met_office_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_WIND_FOLDER")
    elif option == "no_overtopping":
        met_office_wave_folder = os.environ.get("MET_OFFICE_NO_OVERTOP_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_NO_OVERTOP_WIND_FOLDER")
    elif option == "storm_bert":
        met_office_wave_folder = os.environ.get("MET_OFFICE_STORM_BERT_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_STORM_BERT_WIND_FOLDER")

    dawlish_water_level_file = os.environ.get("WATER_LEVEL_FILE")
    penzance_water_level_file = os.environ.get("PENZANCE_WATER_LEVEL_FILE")

    return (
        met_office_wave_folder,
        met_office_wind_folder,
        dawlish_water_level_file,
        penzance_water_level_file,
    )


def getNumericValue(input_value):
    """Get numeric value

    Args:
        input_value (string): String representing number

    Returns:
        integer: Numeric value
    """

    return int(input_value) if isinstance(input_value, str) else input_value


def convert_df_to_json_data(original_df):
    if not original_df.empty:
        original_df["time"] = original_df.apply(
            lambda row: row.Time.strftime("%a, %d %b %Y %H:%M:%S GMT"), axis=1
        )
        original_df = original_df.drop(["Time"], axis=1)
        original_json_data = original_df.to_json(orient="records")
        json_data = json.loads(original_json_data)
    else:
        json_data = []
    return json_data


def get_query_params_values(
    start_date_name,
    sig_wave_height_name,
    freeboard_name,
    mean_wave_period_name,
    mean_wave_dir_name,
    wind_speed_name,
    wind_direction_name,
):
    """Get query parameters values

    Args:
        start_date_name (string): Parameter's name of forecast start date
        sig_wave_height_name (_type_): Parameter's name of significant wave height variable
        freeboard_name (_type_): Parameter's name of freeboard variable
        mean_wave_period_name (_type_): Parameter's name of mean wave period variable
        mean_wave_dir_name (_type_): Parameter's name of mean wave direction variable
        wind_speed_name (_type_): Parameter's name of wind speed variable
        wind_direction_name (_type_): Parameter's name of wind direction variable

    Returns:
        Tuple: Values of forecast start date, significant wave height, freeboard, mean wave period, mean wave direction, wind speed and wind direction
    """

    start_date = request.args.get(start_date_name, datetime.now().date())
    date_object = (
        datetime.strptime(start_date, "%d-%m-%Y").date()
        if isinstance(start_date, str)
        else start_date
    )
    sig_wave_height = utils.getNumericValue(request.args.get(sig_wave_height_name, 0))
    freeboard = utils.getNumericValue(request.args.get(freeboard_name, 0))
    mean_wave_period = utils.getNumericValue(request.args.get(mean_wave_period_name, 0))
    mean_wave_dir = utils.getNumericValue(request.args.get(mean_wave_dir_name, 0))
    wind_speed = utils.getNumericValue(request.args.get(wind_speed_name, 0))
    wind_direction = utils.getNumericValue(request.args.get(wind_direction_name, 0))
    return (
        date_object,
        sig_wave_height,
        freeboard,
        mean_wave_period,
        mean_wave_dir,
        wind_speed,
        wind_direction,
    )


def all_variables_with_initial_values(
    sig_wave_height,
    freeboard,
    mean_wave_period,
    mean_wave_dir,
    wind_speed,
    wind_direction,
):
    """All variables have zero value

    Args:
        sig_wave_height (integer): Significant wave height value
        freeboard (integer): Freeboard value
        mean_wave_period (integer): Mean wave period value
        mean_wave_dir (integer): Mean wave direction value
        wind_speed (integer): Wind speed value
        wind_direction (integer): Wind direction value

    Returns:
        bool: Flag is True when all variables have zero value, False otherwise
    """
    
    return (
        sig_wave_height == 0
        and freeboard == 0
        and mean_wave_period == 0
        and mean_wave_dir == 0
        and wind_speed == 0
        and wind_direction == 0
    )
