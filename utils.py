import os 
from dotenv import load_dotenv

def loadConfigFile():
    environment = os.getenv("SPLASH_ENV")

    if environment == 'local':
        config_file_path = "config/.env"
    elif environment == 'staging':
        config_file_path = "config/.env.staging"
    else: 
        config_file_path = "config/.env.production"

    load_dotenv(config_file_path)


def getLocationDataPaths(option: str):    
    if option == "dawlish" or option == "penzance":
        met_office_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_WIND_FOLDER")
        water_level_file = os.environ.get("WATER_LEVEL_FILE")
        penzance_water_level_file = os.environ.get("PENZANCE_WATER_LEVEL_FILE")
    elif option == "no_overtopping":
        met_office_wave_folder = os.environ.get("MET_OFFICE_NO_OVERTOP_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_NO_OVERTOP_WIND_FOLDER")
        water_level_file = os.environ.get("WATER_LEVEL_FILE")
        penzance_water_level_file = os.environ.get("PENZANCE_WATER_LEVEL_FILE")
    elif option == "storm_bert":
        met_office_wave_folder = os.environ.get("MET_OFFICE_STORM_BERT_WAVE_FOLDER")
        met_office_wind_folder = os.environ.get("MET_OFFICE_STORM_BERT_WIND_FOLDER")
        water_level_file = os.environ.get("WATER_LEVEL_FILE")
        penzance_water_level_file = os.environ.get("PENZANCE_WATER_LEVEL_FILE")


    return met_office_wave_folder, met_office_wind_folder, water_level_file, penzance_water_level_file


def getNumericValue(input_value):
    return int(input_value) if isinstance(input_value, str) else input_value