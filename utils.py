import os 
from dotenv import load_dotenv
import pandas as pd
from flask import request
from datetime import datetime
import utils
import json

def loadConfigFile():
    environment = os.getenv("SPLASH_ENV")

    if environment == 'local':
        config_file_path = "config/.env"
    elif environment == 'staging':
        config_file_path = "config/.env.staging"
    elif environment == 'docker':
        config_file_path = "config/.env.docker"
    else:
        config_file_path = "config/.env.production"

    load_dotenv(config_file_path)


def getLocationDataPaths(option: str):
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

    return met_office_wave_folder, met_office_wind_folder, dawlish_water_level_file, penzance_water_level_file


def getNumericValue(input_value):
    return int(input_value) if isinstance(input_value, str) else input_value


def convert_df_to_json_data(original_df):
    if not original_df.empty:
        original_df['time'] = original_df.apply(lambda row: row.Time.strftime("%a, %d %b %Y %H:%M:%S GMT"), axis=1)
        original_df = original_df.drop(['Time'], axis=1)
        original_json_data = original_df.to_json(orient='records')
        json_data = json.loads(original_json_data)
    else:
        json_data = []
    return json_data


def get_query_params_values(start_date_name, sig_wave_height_name, freeboard_name, mean_wave_period_name, mean_wave_dir_name, wind_speed_name, wind_direction_name):
    start_date = request.args.get(start_date_name, datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date
    sig_wave_height =  utils.getNumericValue(request.args.get(sig_wave_height_name, 0))
    freeboard =  utils.getNumericValue(request.args.get(freeboard_name, 0))
    mean_wave_period =  utils.getNumericValue(request.args.get(mean_wave_period_name, 0))
    mean_wave_dir =  utils.getNumericValue(request.args.get(mean_wave_dir_name, 0))
    wind_speed =  utils.getNumericValue(request.args.get(wind_speed_name, 0))
    wind_direction =  utils.getNumericValue(request.args.get(wind_direction_name, 0))
    return date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction 
