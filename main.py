from flask import Flask, jsonify, request
import dawlish_final_digital_twin_script_upgraded as ddt
import penzance_final_digital_twin_script_upgraded as pdt
import pandas as pd
from datetime import datetime
import os
import utils
import json


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
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    ddt.load_models(SPLASH_DT_Dawlish_models_folder)

    seawall_crest_overtopping_df, railway_line_overtopping_df = ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)
    seawall_crest_overtopping_df = seawall_crest_overtopping_df.rename(columns={'Confidence': 'confidence', 'Overtopping Count': 'overtopping_count'})
    railway_line_overtopping_df = railway_line_overtopping_df.rename(columns={'Confidence': 'confidence', 'Overtopping Count': 'overtopping_count'})
   
    seawall_crest_overtopping = utils.convert_df_to_json_data(seawall_crest_overtopping_df)
    railway_line_overtopping = utils.convert_df_to_json_data(railway_line_overtopping_df)
 

    return jsonify({
        "seawall_crest_overtopping": seawall_crest_overtopping,
        "railway_line_overtopping": railway_line_overtopping
    })


@app.route('/splash/penzance/wave-overtopping', methods=['GET'])
def get_penzance_wave_overtopping():   
    option = request.args.get('option', 'penzance')
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)

    seawall_crest_overtopping_df, seawall_crest_sheltered_overtopping_df = pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)       
    seawall_crest_overtopping_df = seawall_crest_overtopping_df.rename(columns={'Confidence': 'confidence', 'Overtopping Count': 'overtopping_count'})
    seawall_crest_sheltered_overtopping_df = seawall_crest_sheltered_overtopping_df.rename(columns={'Confidence': 'confidence', 'Overtopping Count': 'overtopping_count'})

    seawall_crest_overtopping = utils.convert_df_to_json_data(seawall_crest_overtopping_df)
    seawall_crest_sheltered_overtopping = utils.convert_df_to_json_data(seawall_crest_sheltered_overtopping_df)

    # Return the data as a JSON response
    return jsonify({
        "seawall_crest_overtopping": seawall_crest_overtopping,
        "seawall_crest_sheltered_overtopping": seawall_crest_sheltered_overtopping
    })


@app.route('/splash/dawlish/significant-wave-height', methods=['GET'])
def get_dawlish_significant_wave_height():
    option = request.args.get('option', 'dawlish') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    interpolated_DawlishTwin_dataset, overtopping_times_by_feature_df = ddt.get_feature_and_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Hs')
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.rename(columns={'Hs': 'significant_wave_height', 'time': 'Time'})
    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Hs': 'significant_wave_height', 'overtopping_time': 'Time'})
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.drop(['Freeboard', 'RF1_Confidence', 'RF1_Final_Predictions', 'RF2_Overtopping_Count', 'RF3_Confidence', 
                                                                              'RF3_Final_Predictions', 'Tm', 'Wind(m/s)', 'shoreWaveDir', 'shoreWindDir'], axis=1)

    significant_wave_height = utils.convert_df_to_json_data(interpolated_DawlishTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)

    return jsonify({
        "significant_wave_heights": significant_wave_height,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/dawlish/tidal-level', methods=['GET'])
def get_dawlish_water_level():
    option = request.args.get('option', 'dawlish') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    ds_start_date = final_DawlishTwin_dataset_adjusted['time'].min()
    ds_end_date = final_DawlishTwin_dataset_adjusted['time'].max()

    all_vars_with_initial_values = utils.all_variables_with_initial_values(sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    interpolated_DawlishTwin_dataset = ddt.extract_water_level_for_range(final_DawlishTwin_dataset_adjusted, ds_start_date, ds_end_date, all_vars_with_initial_values)
    overtopping_times_by_feature_df = ddt.get_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Freeboard')
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.reset_index()
    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Freeboard': 'tidal_level', 'overtopping_time': 'Time'})
    
    tidal_level_data = utils.convert_df_to_json_data(interpolated_DawlishTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)
 
    return jsonify({
        "tidal_levels": tidal_level_data,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/dawlish/wind-speed', methods=['GET'])
def get_dawlish_wind_speed():
    option = request.args.get('option', 'dawlish') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    ddt.process_wave_overtopping(final_DawlishTwin_dataset_adjusted)

    interpolated_DawlishTwin_dataset, overtopping_times_by_feature_df = ddt.get_feature_and_overtopping_times_data(final_DawlishTwin_dataset_adjusted, 'Wind(m/s)')
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.rename(columns={'Wind(m/s)': 'wind_speed', 'time': 'Time'})
    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Wind(m/s)': 'wind_speed', 'overtopping_time': 'Time'})
    interpolated_DawlishTwin_dataset = interpolated_DawlishTwin_dataset.drop(['Freeboard', 'Hs', 'RF1_Confidence', 'RF1_Final_Predictions', 'RF2_Overtopping_Count', 'RF3_Confidence', 
                                                                              'RF3_Final_Predictions', 'Tm', 'shoreWaveDir', 'shoreWindDir'], axis=1)
    wind_speed_data = utils.convert_df_to_json_data(interpolated_DawlishTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)
 
    return jsonify({
        "wind_speeds": wind_speed_data,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/penzance/significant-wave-height', methods=['GET'])
def get_penzance_significant_wave_height():
    option = request.args.get('option', 'penzance') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)

    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)

    interpolated_PenzanceTwin_dataset, overtopping_times_by_feature_df = pdt.get_feature_and_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Hs')
    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.rename(columns={'Hs': 'significant_wave_height', 'time': 'Time'})
    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Hs': 'significant_wave_height', 'overtopping_time': 'Time'})
    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.drop(['Tm', 'shoreWaveDir', 'Wind(m/s)', 'Wind Speed_wind', 'Wind Direction_dir', 'water_level_wl', 
                                                                                'Freeboard', 'RF1_Final_Predictions', 'Selected_Model', 'shoreWindDir'], axis=1)

    significant_wave_height_data = utils.convert_df_to_json_data(interpolated_PenzanceTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)

    return jsonify({
        "significant_wave_heights": significant_wave_height_data,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/penzance/tidal-level', methods=['GET'])
def get_penzance_tidal_level():
    option = request.args.get('option', 'penzance') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)

    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)

    ds_start_date = final_Penzance_Twin_dataset_adjusted['time'].min()
    ds_end_date = final_Penzance_Twin_dataset_adjusted['time'].max()
    all_vars_with_initial_values = utils.all_variables_with_initial_values(sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    interpolated_PenzanceTwin_dataset = pdt.extract_hourly_water_level_data(final_Penzance_Twin_dataset_adjusted, ds_start_date, ds_end_date, all_vars_with_initial_values)
    overtopping_times_by_feature_df = pdt.get_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Freeboard')
    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.reset_index()

    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Freeboard': 'tidal_level', 'overtopping_time': 'Time'})

    tidal_level_data = utils.convert_df_to_json_data(interpolated_PenzanceTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)

    return jsonify({
        "tidal_levels": tidal_level_data,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/penzance/wind-speed', methods=['GET'])
def get_penzance_wind_speed_level():
    option = request.args.get('option', 'penzance') 
    date_object, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction  = utils.get_query_params_values('start_date', 'sig_wave_height', 'freeboard', 'mean_wave_period', 'mean_wave_dir', 'wind_speed', 'wind_direction')

    pdt.setInputFolderPaths(option)
    final_Penzance_Twin_dataset, start_time, start_date_block = pdt.get_digital_twin_dataset(date_object)
    final_Penzance_Twin_dataset_adjusted = pdt.adjust_overtopping_features(final_Penzance_Twin_dataset, sig_wave_height, freeboard, mean_wave_period, mean_wave_dir, wind_speed, wind_direction)
    
    pdt.load_model_files(SPLASH_DT_Penzance_models_folder)
    final_Penzance_Twin_dataset_adjusted = pdt.add_selected_model_col(final_Penzance_Twin_dataset_adjusted, start_time)
    pdt.process_wave_overtopping(final_Penzance_Twin_dataset_adjusted, start_time)


    interpolated_PenzanceTwin_dataset, overtopping_times_by_feature_df = pdt.get_feature_and_overtopping_times_data(final_Penzance_Twin_dataset_adjusted, 'Wind(m/s)')
    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.rename(columns={'Wind(m/s)': 'wind_speed', 'time': 'Time'})
    overtopping_times_by_feature_df = overtopping_times_by_feature_df.rename(columns={'Wind(m/s)': 'wind_speed', 'overtopping_time': 'Time'})
    interpolated_PenzanceTwin_dataset = interpolated_PenzanceTwin_dataset.drop(['Hs', 'Tm', 'shoreWaveDir', 'shoreWindDir', 'Freeboard', 
                                                                              'Wind Speed_wind', 'Wind Direction_dir', 'water_level_wl', 'Selected_Model', 'RF1_Final_Predictions'], axis=1)

    wind_speed_data = utils.convert_df_to_json_data(interpolated_PenzanceTwin_dataset)
    overtopping_times = utils.convert_df_to_json_data(overtopping_times_by_feature_df)

    return jsonify({
        "wind_speeds": wind_speed_data,
        "overtopping_times": overtopping_times
    })


@app.route('/splash/dawlish/significant-wave-height/spatial-data', methods=['GET'])
def get_dawlish_swh_spatial_data():
    option = request.args.get('option', 'dawlish') 
    start_date = request.args.get('start_date', datetime.now().date())
    date_object = datetime.strptime(start_date, "%d-%m-%Y").date() if isinstance(start_date, str) else start_date

    ddt.setInputFolderPaths(option)
    final_DawlishTwin_dataset = ddt.get_digital_twin_dataset(date_object)
    final_DawlishTwin_dataset_adjusted = ddt.adjust_overtopping_features(final_DawlishTwin_dataset, 0, 0, 0, 0, 0, 0)

    ddt.load_models(SPLASH_DT_Dawlish_models_folder)
    results = ddt.generate_significant_wave_height()
    return json.dumps(results, indent=4)



if __name__ == '__main__':
    if DEBUG == True:
        print("SPLASH_DT_Dawlish_models_folder = ", SPLASH_DT_Dawlish_models_folder)
        print("SPLASH_DT_Penzance_models_folder = ", SPLASH_DT_Penzance_models_folder)

    if os.environ.get("SPLASH_ENV")=="docker":
        app.run(debug=DEBUG, host="0.0.0.0", port=8080)
    else:
        app.run(debug=DEBUG, port=8080)
