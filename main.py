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

    seawall_crest_overtopping_df, railway_line_overtopping_df = ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)
    seawall_crest_overtopping = utils.convert_df_to_json_data(seawall_crest_overtopping_df)
    railway_line_overtopping = utils.convert_df_to_json_data(railway_line_overtopping_df)
 

    return jsonify({
        "seawall_crest_overtopping": eval(seawall_crest_overtopping),
        "railway_line_overtopping": eval(railway_line_overtopping)
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

    seawall_crest_overtopping_df, seawall_crest_sheltered_overtopping_df = pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)       
    seawall_crest_overtopping = utils.convert_df_to_json_data(seawall_crest_overtopping_df)
    seawall_crest_sheltered_overtopping = utils.convert_df_to_json_data(seawall_crest_sheltered_overtopping_df)

    # Return the data as a JSON response
    return jsonify({
        "seawall_crest_overtopping": eval(seawall_crest_overtopping),
        "seawall_crest_sheltered_overtopping": eval(seawall_crest_sheltered_overtopping)
    })


@app.route('/splash/dawlish/significant-wave-height', methods=['GET'])
def get_dawlish_significant_wave_height():
    option = request.args.get('option', 'dawlish') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, 0, 0, 0, 0, 0, 0)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    interpolated_DawlishTwin_dataset, overtopping_times_by_feature = ddt.get_feature_and_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Hs')
    significant_wave_height_list = utils.convert_variable_df_to_list(interpolated_DawlishTwin_dataset, 'significant_wave_height', 'Hs', 'time')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'significant_wave_height', 'Hs', 'overtopping_time')

    return jsonify({
        "significant_wave_heights": significant_wave_height_list,
        "overtopping_times": overtopping_times_list
    })


@app.route('/splash/dawlish/tidal-level', methods=['GET'])
def get_dawlish_water_level():
    option = request.args.get('option', 'dawlish') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, 0, 0, 0, 0, 0, 0)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    ds_start_date = final_DawlishTwin_dataset_adjusted['time'].min()
    ds_end_date = final_DawlishTwin_dataset_adjusted['time'].max()
    interpolated_DawlishTwin_dataset = ddt.extract_water_level_for_range(ds_start_date, ds_end_date)

    overtopping_times_by_feature = ddt.get_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Freeboard')
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.reset_index()
    tidal_level_data_list = utils.convert_variable_df_to_list(interpolated_DawlishTwin_dataset, 'tidal_level', 'water_level', 'datetime')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'tidal_level', 'Freeboard', 'overtopping_time')

    return jsonify({
        "tidal_levels": tidal_level_data_list,
        "overtopping_times": overtopping_times_list
    })


@app.route('/splash/dawlish/wind-speed', methods=['GET'])
def get_dawlish_wind_speed():
    option = request.args.get('option', 'dawlish') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, 0, 0, 0, 0, 0, 0)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    interpolated_DawlishTwin_dataset, overtopping_times_by_feature = ddt.get_feature_and_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Wind(m/s)')
    tidal_level_data_list = utils.convert_variable_df_to_list(interpolated_DawlishTwin_dataset, 'wind_speed', 'Wind(m/s)', 'time')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'wind_speed', 'Wind(m/s)', 'overtopping_time')

    return jsonify({
        "wind_speeds": tidal_level_data_list,
        "overtopping_times": overtopping_times_list
    })


@app.route('/splash/penzance/significant-wave-height', methods=['GET'])
def get_penzance_significant_wave_height():
    option = request.args.get('option', 'penzance') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, 0, 0, 0, 0, 0, 0)

    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)

    interpolated_PenzanceTwin_dataset, overtopping_times_by_feature = pdt.get_feature_and_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Hs')
    significant_wave_height_list = utils.convert_variable_df_to_list(interpolated_PenzanceTwin_dataset, 'significant_wave_height', 'Hs', 'time')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'significant_wave_height', 'Hs', 'overtopping_time')

    return jsonify({
        "significant_wave_heights": significant_wave_height_list,
        "overtopping_times": overtopping_times_list
    })


@app.route('/splash/penzance/tidal-level', methods=['GET'])
def get_penzance_tidal_level():
    option = request.args.get('option', 'penzance') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, 0, 0, 0, 0, 0, 0)

    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)

    ds_start_date = final_Penzance_Twin_dataset['time'].min()
    ds_end_date = final_Penzance_Twin_dataset['time'].max()
    interpolated_PenzanceTwin_dataset = pdt.extract_hourly_water_level_data(ds_start_date, ds_end_date)
    overtopping_times_by_feature = pdt.get_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Freeboard')

    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.reset_index()
    tidal_level_list = utils.convert_variable_df_to_list(interpolated_PenzanceTwin_dataset, 'tidal_level', 'water_level', 'datetime')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'tidal_level', 'Freeboard', 'overtopping_time')

    return jsonify({
        "tidal_levels": tidal_level_list,
        "overtopping_times": overtopping_times_list
    })


@app.route('/splash/penzance/wind-speed', methods=['GET'])
def get_penzance_wind_speed_level():
    option = request.args.get('option', 'penzance') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, 0, 0, 0, 0, 0, 0)
    
    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)


    interpolated_PenzanceTwin_dataset, overtopping_times_by_feature = pdt.get_feature_and_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Wind(m/s)')
    wind_speed_list = utils.convert_variable_df_to_list(interpolated_PenzanceTwin_dataset, 'wind_speed', 'Wind(m/s)', 'time')
    overtopping_times_list = utils.convert_variable_df_to_list(overtopping_times_by_feature, 'wind_speed', 'Wind(m/s)', 'overtopping_time')

    return jsonify({
        "wind_speeds": wind_speed_list,
        "overtopping_times": overtopping_times_list
    })


if __name__ == '__main__':
  app.run(debug=bool(os.environ.get("DEBUG")), port=8080)