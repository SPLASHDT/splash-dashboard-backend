from flask import Flask, jsonify, request
import dawlish_final_digital_twin_script_upgraded as ddt
import penzance_final_digital_twin_script_upgraded as pdt
import pandas as pd
from datetime import datetime
import os
import utils


utils.loadConfigFile()

SPLASH_DT_Dawlish_models_folder = os.environ.get("DAWLISH_MODELS_FOLDER")
SPLASH_DT_Penzance_models_folder = os.environ.get("PENZANCE_MODELS_FOLDER")
dawlish_lat_seawall = os.environ.get("DAWLISH_LAT_SEAWALL")
dawlish_lon_seawall = os.environ.get("DAWLISH_LON_SEAWALL")
penzance_lat_seawall = os.environ.get("PENZANCE_LAT_SEAWALL")
penzance_lon_seawall = os.environ.get("PENZANCE_LON_SEAWALL")
DEBUG = eval(os.environ.get("DEBUG").capitalize()) # make DEBUG a boolean, we must ensure the string always starts in caps e.g. True/False as that's all eval recognises
app = Flask(__name__)

@app.route('/splash/dawlish/wave-overtopping', methods=['GET'])
def get_dawlish_wave_overtopping():
    option = request.args.get('option', 'dawlish') 
    # Set today's date by default to get current datasets
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date
    sig_wave_height =  utils.getNumericValue(request.args.get('sig_wave_height', 0))
    freeboard =  utils.getNumericValue(request.args.get('freeboard', 0))
    mean_wave_period =  utils.getNumericValue(request.args.get('mean_wave_period', 0))
    mean_wave_dir =  utils.getNumericValue(request.args.get('mean_wave_dir', 0))
    wind_speed =  utils.getNumericValue(request.args.get('wind_speed', 0))
    wind_direction =  utils.getNumericValue(request.args.get('wind_direction', 0))

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    ddt.load_models(SPLASH_DT_Dawlish_models_folder)

    tmp_seawall_crest_overtopping, tmp_railway_line_overtopping = ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    def convert_dataframe_to_list(df):
        if isinstance(df, pd.DataFrame):
            data_list = []
            for index, row in df.iterrows():
                timestamp = row['Time']  # Get the Timestamp object
                formatted_time = timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT") # Format the Timestamp
                data_list.append({
                    "confidence": row['Confidence'],
                    "overtopping_count": row['Overtopping Count'],
                    "time": formatted_time
                })
            return data_list
        elif isinstance(df, list): #if already a list return the list
            return df
        else:
            return []

    seawall_crest_overtopping = convert_dataframe_to_list(tmp_seawall_crest_overtopping)
    railway_line_overtopping = convert_dataframe_to_list(tmp_railway_line_overtopping)

    return jsonify({
        "seawall_crest_overtopping": seawall_crest_overtopping,
        "railway_line_overtopping": railway_line_overtopping
    })


@app.route('/splash/penzance/wave-overtopping', methods=['GET'])
def get_penzance_wave_overtopping():   
    option = request.args.get('option', 'penzance')
    # Set today's date by default to get current datasets
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date
    sig_wave_height =  utils.getNumericValue(request.args.get('sig_wave_height', 0))
    freeboard =  utils.getNumericValue(request.args.get('freeboard', 0))
    mean_wave_period =  utils.getNumericValue(request.args.get('mean_wave_period', 0))
    mean_wave_dir =  utils.getNumericValue(request.args.get('mean_wave_dir', 0))
    wind_speed =  utils.getNumericValue(request.args.get('wind_speed', 0))
    wind_direction =  utils.getNumericValue(request.args.get('wind_direction', 0))

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)

    tmp_seawall_crest_overtopping, tmp_seawall_crest_sheltered_overtopping = pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)

    def convert_dataframe_to_list(df):
        if isinstance(df, pd.DataFrame):
            data_list = []
            for index, row in df.iterrows():
                timestamp = row['Time']  # Get the Timestamp object
                formatted_time = timestamp.strftime("%a, %d %b %Y %H:%M:%S GMT") # Format the Timestamp
                data_list.append({
                    "confidence": row['Confidence'],
                    "overtopping_count": row['Overtopping Count'],
                    "time": formatted_time
                })
            return data_list
        elif isinstance(df, list): #if already a list return the list
            return df
        else:
            return []
        
    seawall_crest_overtopping = convert_dataframe_to_list(tmp_seawall_crest_overtopping)
    seawall_crest_sheltered_overtopping = convert_dataframe_to_list(tmp_seawall_crest_sheltered_overtopping)

    # Return the data as a JSON response
    return jsonify({
        "seawall_crest_overtopping": seawall_crest_overtopping,
        "seawall_crest_sheltered_overtopping": seawall_crest_sheltered_overtopping
    })


if __name__ == '__main__':
    if DEBUG == True:
        print("SPLASH_DT_Dawlish_models_folder = ", SPLASH_DT_Dawlish_models_folder)
        print("SPLASH_DT_Penzance_models_folder = ", SPLASH_DT_Penzance_models_folder)

    if os.environ.get("SPLASH_ENV")=="docker":
        app.run(debug=DEBUG, host="0.0.0.0", port=8080)
    else:
        app.run(debug=DEBUG, port=8080)
