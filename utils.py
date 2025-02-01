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