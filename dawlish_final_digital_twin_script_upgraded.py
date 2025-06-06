# SPDX-FileCopyrightText: © 2025 National Oceanography Centre and University of Plymouth

# SPDX-License-Identifier: MIT

"""SPLASH Digital Twin Dawlish"""

# Script for using the different pretrained machine learning models to predict (1) wave overtopping occurrences and (2) overtopping frequency.
# - Inputs are: Forecasting data (tidal, wind, wave).

# 1.- VHM/Hs (significant Wave Height)
# 2.- VTM02/Tm (Mean Period)
# 3.- VMDR/shoreWaveDir (direction of the waves)
# 4.- water_level/Freeboard (how high the water level is)
# 5.- Wind Direction/shoreWindDir (just the wind direction)
# 6.- Wind Speed/Wind(m/s) (wind speed)

# your final dataset when concatenating all this dataset will have all these variables.
# - Outputs are: Digital Twin interface.

# Authors: Michael McGlade, Nieves G. Valiente, Jennifer Brown, Christopher Stokes, Timothy Poate


# Step 1: Import necessary libraries

import pygrib
import joblib
from IPython.display import display, clear_output
import matplotlib.lines as mlines

import ipywidgets as widgets
from IPython.display import display
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import pandas as pd
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt

import seaborn as sns
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import os
import utils


utils.loadConfigFile()

# Step 2: Extract data from our files

# this is our 3 main folder file paths: wave, wind and wl (water level), we must extract data and concatenate from this these path folders.
Met_office_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
Met_office_wind_folder = os.environ.get("MET_OFFICE_WIND_FOLDER")
wl_file = os.environ.get("WATER_LEVEL_FILE")
state_file = os.environ.get(
    "STATE_FILE"
)  # reminds the code to process each block sequentially.

# We extract the data from these coordinates, this is the Dawlish wave buoy coordinates.
Dawlish_Wave_Buoy_LATITUDE = float(os.environ.get("DAWLISH_WAVE_BUOY_LATITUDE"))
Dawlish_Wave_Buoy_LONGITUDE = float(os.environ.get("DAWLISH_WAVE_BUOY_LONGITUDE"))

# Step 4: Now we load our SPLASH models

SPLASH_DIGITAL_TWIN_models_folder = os.environ.get("DAWLISH_MODELS_FOLDER")

machine_learning_models = {"RF1": {}, "RF2": {}, "RF3": {}, "RF4": {"Regressor": {}}}

# Step 5: This is our slider adjustments, remember we defined this in step 3.
style = {"description_width": "150px"}
slider_layout_design_with_digital_twin = widgets.Layout(width="400px")
Sig_wave_height_slider_output = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Hs (%):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
Mean_Period_Slider = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Tm (%):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
Cross_shore_wave_dir_slider = widgets.FloatSlider(
    value=0,
    min=0,
    max=360,
    step=1,
    description="ShoreWaveDir (°):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
wind_speed_slider = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Wind (m/s) (%):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
Cross_shore_wind_dir_slider = widgets.FloatSlider(
    value=0,
    min=0,
    max=360,
    step=1,
    description="ShoreWindDir (°):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
freeboard_slider = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Freeboard (%):",
    style=style,
    layout=slider_layout_design_with_digital_twin,
)
submit_button = widgets.Button(description="Submit")

rf1_hs_threshold_regularisation = 1.39
rf1_wind_threshold_regularisation = 7.71
rf1_wave_dir_min_regularisation = 49
rf1_wave_dir_max_regularisation = 97

rf3_hs_threshold_regularisation = 1.65
rf3_wind_threshold_regularisation = 8.47
rf3_wave_dir_min_regularisation = 50
rf3_wave_dir_max_regularisation = 93
final_DawlishTwin_dataset = pd.DataFrame()


def setInputFolderPaths(option: str = "dawlish"):
    """Set input folder paths

    Args:
        option (str, optional): Dataset's option name. Defaults to "dawlish".
    """

    global Met_office_wave_folder, Met_office_wind_folder, wl_file
    (
        met_office_wave_folder,
        met_office_wind_folder,
        water_level_file,
        penzance_water_level_file,
    ) = utils.getLocationDataPaths(option)
    Met_office_wave_folder = met_office_wave_folder
    Met_office_wind_folder = met_office_wind_folder
    wl_file = water_level_file


def get_wave_files(block_date):
    """This takes data from the wave block

    Args:
        block_date (Date):  String representing date

    Returns:
        Array: Array of files names
    """

    Current_wave_files = []
    for file_name in os.listdir(Met_office_wave_folder):
        if file_name.startswith(
            f"metoffice_wave_amm15_NWS_WAV_b{block_date.strftime('%Y%m%d')}"
        ):  # this is the unique identification code for each dataset.
            Current_wave_files.append(os.path.join(Met_office_wave_folder, file_name))
    return sorted(Current_wave_files)


def get_wind_file(template, folder, date):
    """Extract data from wind file

    Args:
        template (string): Template of file's name
        folder (string): Folder's name
        date (string): String representing date

    Returns:
        string: Path to wind file
    """

    for file_name in os.listdir(folder):
        if file_name.startswith(template.format(date.strftime("%Y%m%d"))):
            return os.path.join(folder, file_name)
    return None


def extract_wave_data(Current_wave_files):
    """Extract data from the wave file

    Args:
        Current_wave_files (Array): Array of file names

    Raises:
        ValueError: Error's description

    Returns:
        Dataframe: Mean wave data
    """

    wave_data = []
    for file_path in Current_wave_files:
        Met_wave_Dawlish_Buoy = xr.open_dataset(file_path)
        ds_filtered_wave = Met_wave_Dawlish_Buoy.sel(
            latitude=Dawlish_Wave_Buoy_LATITUDE,
            longitude=Dawlish_Wave_Buoy_LONGITUDE,
            method="nearest",
        )
        Met_wave = (
            ds_filtered_wave[["time", "VHM0", "VTM02", "VMDR"]]
            .to_dataframe()
            .reset_index()
        )
        Met_wave = Met_wave.rename(
            columns={
                "time": "datetime",
                "VHM0": "Hs",
                "VTM02": "Tm",
                "VMDR": "shoreWaveDir",
            }
        )  # this confirms we use speicifc variable names which match from our training dataset names for our models.
        Met_wave = Met_wave[["datetime", "Hs", "Tm", "shoreWaveDir"]]
        Met_wave["datetime"] = pd.to_datetime(Met_wave["datetime"])
        wave_data.append(Met_wave)
    if not wave_data:
        raise ValueError("No wave data available for the specified block.")
    combined_wave = pd.concat(wave_data, ignore_index=True)
    return combined_wave.set_index("datetime").resample("3H").mean()


def extract_wind_data(wind_file):
    """Extract wind speed and direction data

    Args:
        wind_file (string): Wind file path

    Raises:
        ValueError: Error's description

    Returns:
        Dataframe: Mean wind data
    """

    data = []
    grbs = pygrib.open(wind_file)
    for grb in grbs:
        if grb.level == 10:
            values = grb.values
            lats, lons = grb.latlons()
            adjust_Daw_lons = np.where(lons > 180, lons - 360, lons)
            distances = np.sqrt(
                (lats - Dawlish_Wave_Buoy_LATITUDE) ** 2
                + (adjust_Daw_lons - Dawlish_Wave_Buoy_LONGITUDE) ** 2
            )
            min_dist_index = np.unravel_index(distances.argmin(), distances.shape)
            value = values[min_dist_index]
            data_date = grb.dataDate
            data_time = grb.dataTime
            Met_office_forecast_time = grb.forecastTime
            init_datetime = datetime.strptime(
                f"{data_date:08d}{data_time:04d}", "%Y%m%d%H%M"
            )
            forecast_datetime = init_datetime + timedelta(
                hours=Met_office_forecast_time
            )
            data.append({"datetime": forecast_datetime, "value": value})
    grbs.close()
    if not data:
        raise ValueError("There is no wind data available forr the specified block.")
    Met_wind = pd.DataFrame(data)
    Met_wind["datetime"] = pd.to_datetime(Met_wind["datetime"])
    Met_wind = Met_wind.drop_duplicates(subset="datetime").set_index("datetime")
    return Met_wind.resample("3H").mean()


def extract_water_level_data():
    """Get water level data

    Returns:
        Dataframe: Interpolated water level data
    """

    water_level = pd.read_csv(
        wl_file,
        sep=r"\s+",
        header=None,
        skiprows=2,
        names=["date", "time", "water_level"],
        engine="python",
    )
    water_level["datetime"] = pd.to_datetime(
        water_level["date"] + " " + water_level["time"], format="%d/%m/%Y %H:%M"
    )
    water_level = water_level.set_index("datetime")[["water_level"]]
    return water_level.resample("3H").interpolate()


def extract_water_level_for_range(start_date, end_date):
    """Extract water level for range

    Args:
        start_date (string): String representing start date
        end_date (string): String representing end date

    Returns:
        Dataframe: Interpolated water level dataframe
    """

    water_level = pd.read_csv(
        wl_file,
        sep=r"\s+",
        header=None,
        skiprows=2,
        names=["date", "time", "water_level"],
        engine="python",
    )
    # Combine date and time columns and convert to datetime
    water_level["datetime"] = pd.to_datetime(
        water_level["date"] + " " + water_level["time"], format="%d/%m/%Y %H:%M"
    )
    water_level = water_level.rename(
        columns={"datetime": "Time", "water_level": "tidal_level"}
    )
    water_level = water_level.set_index("Time")
    water_level = water_level.drop(["date"], axis=1)

    # Filter for the specified date range and resample to hourly
    water_level_filtered = water_level.loc[start_date:end_date]
    return water_level_filtered.resample("1H").interpolate()


def process_block(block_date):
    """Combines all the data from the wind, wave, water level into a single dataset and concatenates the code, which models will eventually process.

    Args:
        block_date (Date): Forecast block's date

    Returns:
        Dataframe: Combined dataframe which holds wind, wave and water level data
    """

    try:
        # Fetch wave, wind speed, and wind direction files for the block_date
        wave_files = get_wave_files(block_date)
        Apply_wind_speed_file = get_wind_file(
            "agl_wind-speed-{}", Met_office_wind_folder, block_date
        )
        wind_direction_file = get_wind_file(
            "agl_wind-direction-{}", Met_office_wind_folder, block_date
        )

        # Use multi-threading to speed up data extraction
        with ThreadPoolExecutor() as executor:
            wave_futureMetOfForecast = executor.submit(extract_wave_data, wave_files)
            wind_speed_futureMetOfForecast = executor.submit(
                extract_wind_data, Apply_wind_speed_file
            )
            wind_direction_futureMetOfForecast = executor.submit(
                extract_wind_data, wind_direction_file
            )
            water_level_future_NOCForecast = executor.submit(extract_water_level_data)

            # Combine all datasets
            wave_data = wave_futureMetOfForecast.result()
            wind_speed_data = wind_speed_futureMetOfForecast.result().rename(
                columns={"value": "Wind Speed"}
            )
            wind_direction_data = wind_direction_futureMetOfForecast.result().rename(
                columns={"value": "Wind Direction"}
            )
            water_level_data = water_level_future_NOCForecast.result()

            # Merge all data into a single DataFrame
            Finale_Dawlish_combined_data = wave_data.resample("1H").mean()
            wind_speed_data = wind_speed_data.resample("1H").mean()
            wind_direction_data = wind_direction_data.resample("1H").mean()
            water_level_data = water_level_data.resample("1H").interpolate()

            Finale_Dawlish_combined_data = Finale_Dawlish_combined_data.join(
                [wind_speed_data, wind_direction_data, water_level_data], how="left"
            )
            first_54_hours = Finale_Dawlish_combined_data.iloc[
                :54
            ]  # First 54 hours remain hourly
            after_54_hours = (
                Finale_Dawlish_combined_data.iloc[54:].resample("3H").asfreq()
            )  # Wave data every 3H
            after_54_hours = after_54_hours.join(
                wind_speed_data, on="datetime", how="left", rsuffix="_wind"
            ).interpolate()
            after_54_hours = after_54_hours.join(
                wind_direction_data, on="datetime", how="left", rsuffix="_dir"
            ).interpolate()
            after_54_hours = after_54_hours.join(
                water_level_data, on="datetime", how="left", rsuffix="_wl"
            ).interpolate()
            Finale_Dawlish_combined_data = pd.concat([first_54_hours, after_54_hours])

        # Log processed date range
        start_date = Finale_Dawlish_combined_data.index.min()
        end_date = Finale_Dawlish_combined_data.index.max()
        print(f"Processed Block: Start Date = {start_date}, End Date = {end_date}")

        # Save the current block date as the last processed state
        with open(state_file, "w") as file:
            file.write(block_date.strftime("%Y-%m-%d"))

        return Finale_Dawlish_combined_data.reset_index()

    except ValueError as e:
        # Handle missing data by automatically using the previous day's forecast
        print(f"Error: {e}")
        print(
            "No data available for today's block. Automatically using the previous day's forecast..."
        )
        previous_block_date = block_date - timedelta(days=1)
        return process_block(previous_block_date)


def get_next_block(start_date):
    """Get block's date

    Args:
        start_date (Date): Forecast block's date

    Returns:
        Date: Block's date
    """

    # Use the current calendar date as today's block date
    # current_date = datetime.now().date()
    current_date = start_date
    print(f"Starting process for today's date: {current_date}")
    return current_date


def get_digital_twin_dataset(start_date):
    """Get digital twin dataset

    Args:
        start_date (Date): Forecast start date

    Returns:
        Dataframe: Digital twin dataframe
    """

    # This indicates all our data entries in our combined block.
    block_data = process_block(get_next_block(start_date))

    if block_data is not None:
        # Select relevant columns and rename for consistency with the model input
        final_DawlishTwin_dataset_tmp = block_data[
            [
                "datetime",
                "Hs",
                "Tm",
                "shoreWaveDir",
                "water_level",
                "Wind Speed",
                "Wind Direction",
            ]
        ].copy()
        final_DawlishTwin_dataset_tmp = final_DawlishTwin_dataset_tmp.rename(
            columns={
                "datetime": "time",
                "Hs": "Hs",
                "Tm": "Tm",
                "shoreWaveDir": "shoreWaveDir",
                "water_level": "Freeboard",
                "Wind Speed": "Wind(m/s)",
                "Wind Direction": "shoreWindDir",
            }
        )

        # Ensure the 'time' column is in datetime format
        final_DawlishTwin_dataset_tmp["time"] = pd.to_datetime(
            final_DawlishTwin_dataset_tmp["time"]
        )

        # Step 3: Create our slider adjustment bar

        def on_submit_clicked(button):
            mechnaism_for_adjusting_slider = adjust_features(
                final_DawlishTwin_dataset_tmp
            )
            clear_output(wait=True)
            process_wave_overtopping(mechnaism_for_adjusting_slider)
            display(
                Sig_wave_height_slider_output,
                Mean_Period_Slider,
                Cross_shore_wave_dir_slider,
                wind_speed_slider,
                Cross_shore_wind_dir_slider,
                freeboard_slider,
                submit_button,
            )  # can rename these if needed
            submit_button = widgets.Button(description="Submit", button_style="primary")
            submit_button.on_click(on_submit_clicked)
            process_wave_overtopping(final_DawlishTwin_dataset_tmp)
            display(
                Sig_wave_height_slider_output,
                Mean_Period_Slider,
                Cross_shore_wave_dir_slider,
                wind_speed_slider,
                Cross_shore_wind_dir_slider,
                freeboard_slider,
                submit_button,
            )

    else:
        print("No block data")

    return final_DawlishTwin_dataset_tmp


def load_models(SPLASH_DIGITAL_TWIN_models_folder):
    """Load models

    Args:
        SPLASH_DIGITAL_TWIN_models_folder (string): Path to digital twin models folder
    """

    for file_name in os.listdir(SPLASH_DIGITAL_TWIN_models_folder):
        file_path = os.path.join(SPLASH_DIGITAL_TWIN_models_folder, file_name)
        if "RF1" in file_name:
            if "T24" in file_name:
                machine_learning_models["RF1"]["T24"] = joblib.load(file_path)
            elif "T48" in file_name:
                machine_learning_models["RF1"]["T48"] = joblib.load(file_path)
            elif "T72" in file_name:
                machine_learning_models["RF1"]["T72"] = joblib.load(file_path)
        elif "RF2" in file_name:
            if "T24" in file_name:
                machine_learning_models["RF2"]["T24"] = joblib.load(file_path)
            elif "T48" in file_name:
                machine_learning_models["RF2"]["T48"] = joblib.load(file_path)
            elif "T72" in file_name:
                machine_learning_models["RF2"]["T72"] = joblib.load(file_path)
        elif "RF3" in file_name:
            if "T24" in file_name:
                machine_learning_models["RF3"]["T24"] = joblib.load(file_path)
            elif "T48" in file_name:
                machine_learning_models["RF3"]["T48"] = joblib.load(file_path)
            elif "T72" in file_name:
                machine_learning_models["RF3"]["T72"] = joblib.load(file_path)
        elif "RF4" in file_name:
            if "T24" in file_name:
                machine_learning_models["RF4"]["Regressor"]["T24"] = joblib.load(
                    file_path
                )
            elif "T48" in file_name:
                machine_learning_models["RF4"]["Regressor"]["T48"] = joblib.load(
                    file_path
                )
            elif "T72" in file_name:
                machine_learning_models["RF4"]["Regressor"]["T72"] = joblib.load(
                    file_path
                )


def revise_rf1_prediction(rf1_prediction, row):
    """Revise rf1 prediction

    Args:
        rf1_prediction (integer): Prediction's value
        row (Series): Features data row

    Returns:
        integer: Final prediction's value
    """

    hs_value_sweetspot = row["Hs"] > rf1_hs_threshold_regularisation
    wind_value_sweetspot = row["Wind(m/s)"] > rf1_wind_threshold_regularisation
    wave_dir_sweetspot = (
        rf1_wave_dir_min_regularisation
        <= row["shoreWaveDir"]
        <= rf1_wave_dir_max_regularisation
    )
    return (
        0
        if rf1_prediction == 1
        and not (hs_value_sweetspot or wind_value_sweetspot or wave_dir_sweetspot)
        else rf1_prediction
    )


def revise_rf3_prediction(rf3_prediction, row):
    """Revise rf3 prediction

    Args:
        rf3_prediction (integer): Prediction's value
        row (Series): Features data row

    Returns:
        integer: Final prediction's value
    """

    hs_value_sweetspot = row["Hs"] > rf3_hs_threshold_regularisation
    wind_value_sweetspot = row["Wind(m/s)"] > rf3_wind_threshold_regularisation
    wave_dir_sweetspot = (
        rf3_wave_dir_min_regularisation
        <= row["shoreWaveDir"]
        <= rf3_wave_dir_max_regularisation
    )
    return (
        0
        if rf3_prediction == 1
        and not (hs_value_sweetspot or wind_value_sweetspot or wave_dir_sweetspot)
        else rf3_prediction
    )


# Step 6: Now we assign confidence for our model.
def get_confidence_color(confidence, is_railway=False):
    """Get colour according to confidence value

    Args:
        confidence (float): Confidence value

    Returns:
        string: Colour's name
    """

    try:
        confidence = float(confidence)

        if is_railway:
            if confidence > 0.6:
                return "#00008B"  # High confidence
            elif 0.4 < confidence <= 0.6:
                return "#4682B4"  # Medium confidence
            return "#4682B4"
        else:
            if confidence > 0.8:
                return "#00008B"  # High confidence
            elif 0.5 < confidence <= 0.8:
                return "#4682B4"  # Medium confidence
            else:
                return "aqua"

    except (ValueError, TypeError):
        return "gray"


def adjust_features(df):
    """Adjust wave and atmospheric features

    Args:
        df (Dataframe): Initial digital twin dataframe

    Returns:
        Dataframe: Dataframe with adjusted features values
    """

    df_adjusted_slideronly = df.copy()
    df_adjusted_slideronly["Hs"] *= 1 + Sig_wave_height_slider_output.value / 100
    df_adjusted_slideronly["Tm"] *= 1 + Mean_Period_Slider.value / 100
    df_adjusted_slideronly["shoreWaveDir"] = Cross_shore_wave_dir_slider.value
    df_adjusted_slideronly["Wind(m/s)"] *= 1 + wind_speed_slider.value / 100
    df_adjusted_slideronly["shoreWindDir"] = Cross_shore_wind_dir_slider.value
    df_adjusted_slideronly["Freeboard"] *= 1 + freeboard_slider.value / 100
    return df_adjusted_slideronly


def adjust_overtopping_features(
    df,
    sig_wave_height,
    freeboard,
    mean_wave_period,
    mean_wave_dir,
    wind_speed,
    wind_direction,
):
    """Adjust wave and atmospheric features

    Args:
        df (Dataframe): Initial digital twin dataframe
        sig_wave_height (integer): Significant wave height value in percentage
        freeboard (_type_): Freeboard value in percentage
        mean_wave_period (_type_): Mean wave period value in percentage
        mean_wave_dir (_type_): Mean wave direction value in degrees
        wind_speed (_type_): Wind speed value in percentage
        wind_direction (_type_): Wind direction value in degrees

    Returns:
        Dataframe: Dataframe with adjusted features values
    """

    df_adjusted_slideronly = df.copy()
    df_adjusted_slideronly["Hs"] *= 1 + sig_wave_height / 100
    df_adjusted_slideronly["Tm"] *= 1 + mean_wave_period / 100
    df_adjusted_slideronly["shoreWaveDir"] = mean_wave_dir
    df_adjusted_slideronly["Wind(m/s)"] *= 1 + wind_speed / 100
    df_adjusted_slideronly["shoreWindDir"] = wind_direction
    df_adjusted_slideronly["Freeboard"] *= 1 + freeboard / 100
    return df_adjusted_slideronly


def adjust_freeboard_only(df, freeboard):
    """Adjust freeboard value only

    Args:
    df (Dataframe): Initial digital twin dataframe
    freeboard (_type_): Freeboard value in percentage

    Returns:
    Dataframe: Dataframe with adjusted features values
    """

    df_adjusted_slideronly = df.copy()
    df_adjusted_slideronly["tidal_level"] *= 1 + freeboard / 100
    return df_adjusted_slideronly


def process_wave_overtopping(df_adjusted_slideronly):
    """Process wave overtopping

    Args:
        df_adjusted_slideronly (Dataframe): Main dataframe with adjusted wave and atmospheric variables

    Returns:
        Dataframes: First location and second location wave-overtopping-events dataframes
    """

    time_stamps = df_adjusted_slideronly["time"].dropna()
    overtopping_counts_rf1_rf2 = []
    overtopping_counts_rf3_rf4 = []
    rf1_confidences_GINI = []
    rf3_confidences_GINI = []
    rf1_predictions = []

    for idx, row in df_adjusted_slideronly.iterrows():
        if pd.isna(row["time"]):
            continue

        # Step 7: Now we must ensure we sleect the correct pretrained model for assessing our forecasting data.

        time_difference_from_MetOffice_forecast_data = (
            row["time"] - df_adjusted_slideronly["time"].iloc[0]
        ).total_seconds() / 3600

        if time_difference_from_MetOffice_forecast_data < 24:  # T24 model
            selected_model = "T24"
        elif 24 <= time_difference_from_MetOffice_forecast_data < 48:  # T48 model
            selected_model = "T48"
        else:  # T72 model
            selected_model = "T72"
        input_data = (
            row[["Hs", "Tm", "shoreWaveDir", "Wind(m/s)", "shoreWindDir", "Freeboard"]]
            .to_frame()
            .T
        )

        # Step 8: Now we can start making our predictions.

        # This generates our rig 1 binary predictions
        rf1_model_DIGITALTWIN = machine_learning_models["RF1"][selected_model]
        rf1_prediction = rf1_model_DIGITALTWIN.predict(input_data)[0]
        rf1_confidence = rf1_model_DIGITALTWIN.predict_proba(input_data)[0][1]
        rf1_confidences_GINI.append(rf1_confidence)  # % confidence as color

        final_rf1_prediction = revise_rf1_prediction(rf1_prediction, row)
        rf1_predictions.append(final_rf1_prediction)

        if final_rf1_prediction == 0:
            overtopping_counts_rf1_rf2.append(0)
            overtopping_counts_rf3_rf4.append(0)
        else:
            # Run RF2 model (overtopping count)
            rf2_model = machine_learning_models["RF2"][selected_model]
            rf2_prediction = rf2_model.predict(input_data)[0]
            overtopping_counts_rf1_rf2.append(rf2_prediction)

            # Run RF3 model (secondary binary classifier)
            rf3_model = machine_learning_models["RF3"][selected_model]
            rf3_prediction = rf3_model.predict(input_data)[0]
            rf3_confidence = rf3_model.predict_proba(input_data)[0][1]
            rf3_confidences_GINI.append(rf3_confidence)

            # Apply threshold correction for RF3
            final_rf3_prediction = revise_rf3_prediction(rf3_prediction, row)
            if final_rf3_prediction == 0:
                overtopping_counts_rf3_rf4.append(0)
            else:
                # Run RF4 model (regression model)
                rf4_regressor = machine_learning_models["RF4"]["Regressor"][
                    selected_model
                ]  # again if rf3 says 1 then this will trigger rf4, rememeber if rf3 says 0 this means rf4 is not triggered
                rf4_prediction = rf4_regressor.predict(input_data)[0]
                overtopping_counts_rf3_rf4.append(min(rf4_prediction, rf2_prediction))

    min_len = len(df_adjusted_slideronly)
    while len(rf3_confidences_GINI) < min_len:
        rf3_confidences_GINI.append(0)
    while len(overtopping_counts_rf3_rf4) < min_len:
        overtopping_counts_rf3_rf4.append(0)

    df_adjusted_slideronly["RF1_Final_Predictions"] = rf1_predictions
    df_adjusted_slideronly["RF2_Overtopping_Count"] = overtopping_counts_rf1_rf2
    df_adjusted_slideronly["RF3_Final_Predictions"] = overtopping_counts_rf3_rf4
    df_adjusted_slideronly["RF1_Confidence"] = rf1_confidences_GINI
    df_adjusted_slideronly["RF3_Confidence"] = rf3_confidences_GINI

    # Prepare DataFrames for Plotly
    data_rf1_rf2 = pd.DataFrame(
        {
            "Time": time_stamps,
            "Overtopping Count": overtopping_counts_rf1_rf2,
            "Confidence": rf1_confidences_GINI,
        }
    )

    data_rf3_rf4 = pd.DataFrame(
        {
            "Time": time_stamps,
            "Overtopping Count": overtopping_counts_rf3_rf4,
            "Confidence": rf3_confidences_GINI,
        }
    )

    # plot_overtopping_graphs(df_adjusted_slideronly, overtopping_counts_rf1_rf2, overtopping_counts_rf3_rf4, rf1_confidences_GINI, rf3_confidences_GINI)

    return data_rf1_rf2, data_rf3_rf4


def plot_overtopping_graphs(
    df_adjusted_slideronly_tmp,
    overtopping_counts_rf1_rf2,
    overtopping_counts_rf3_rf4,
    rf1_confidences_GINI,
    rf3_confidences_GINI,
):
    """Plot overtopping graphs using Matplotlib

    Args:
        df_adjusted_slideronly_tmp (Dataframe): Main dataframe with adjusted wave and atmospheric variables
        overtopping_counts_rf1_rf2 (List): Overtopping counts list of first location
        overtopping_counts_rf3_rf4 (List): Overtopping counts list of second location
        rf1_confidences_GINI (List): Confidence values list of overtopping events prediction for first location
        rf3_confidences_GINI (List): Confidence values list of overtopping events prediction for second location
    """

    # Step 9, now we plot our results
    clear_output(wait=True)
    fig, (axes1_DG_Plot, axes2_DG_Plot) = plt.subplots(2, 1, figsize=(16, 10), dpi=300)
    time_stamps = df_adjusted_slideronly_tmp["time"]
    start_date = time_stamps.iloc[0]
    end_date = time_stamps.iloc[-1]
    xticks = df_adjusted_slideronly_tmp["time"]

    # Plot for Rig 1
    for i, count in enumerate(overtopping_counts_rf1_rf2):
        if count == 0:
            axes1_DG_Plot.scatter(
                time_stamps.iloc[i],
                count,
                marker="x",
                color="black",
                s=80,
                linewidths=1.5,
            )
        else:
            color = get_confidence_color(rf1_confidences_GINI[i])
            axes1_DG_Plot.scatter(
                time_stamps.iloc[i],
                count,
                marker="o",
                color=color,
                s=75,
                edgecolor="black",
                linewidth=1,
            )

    axes1_DG_Plot.axhline(
        y=6, color="black", linestyle="--", linewidth=1, label="25% IQR (6)"
    )
    axes1_DG_Plot.axhline(
        y=54, color="black", linestyle="--", linewidth=1, label="75% IQR (54)"
    )
    axes1_DG_Plot.set_ylim(-10, 120)
    axes1_DG_Plot.set_xlim(
        df_adjusted_slideronly_tmp["time"].min(),
        df_adjusted_slideronly_tmp["time"].max(),
    )
    axes1_DG_Plot.set_xticks(df_adjusted_slideronly_tmp["time"])
    axes1_DG_Plot.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    axes1_DG_Plot.tick_params(axis="x", rotation=90, labelsize=8)
    axes1_DG_Plot.tick_params(axis="x", rotation=90, labelsize=8)
    axes1_DG_Plot.tick_params(axis="y", labelsize=8)
    axes1_DG_Plot.set_title(
        "Dawlish Seawall Crest", loc="center", fontsize=12, fontweight="bold"
    )
    axes1_DG_Plot.set_ylabel(
        "No. of Overtopping Occurences (Per 10 Mins)", fontsize=10, labelpad=10
    )

    # Plot for Rig 2
    for i, count in enumerate(overtopping_counts_rf3_rf4):
        if count == 0:
            axes2_DG_Plot.scatter(
                time_stamps.iloc[i],
                count,
                marker="x",
                color="black",
                s=80,
                linewidths=1.5,
            )
        else:
            # Apply the adjusted color logic for the railway plot
            color = get_confidence_color(rf3_confidences_GINI[i], is_railway=True)
            axes2_DG_Plot.scatter(
                time_stamps.iloc[i],
                count,
                marker="o",
                color=color,
                s=75,
                edgecolor="black",
                linewidth=1,
            )

    axes2_DG_Plot.axhline(
        y=2, color="black", linestyle="--", linewidth=1, label="25% IQR (2)"
    )
    axes2_DG_Plot.axhline(
        y=9, color="black", linestyle="--", linewidth=1, label="75% IQR (9)"
    )
    axes2_DG_Plot.set_ylim(-5, 120)
    axes2_DG_Plot.set_xlim(
        df_adjusted_slideronly_tmp["time"].min(),
        df_adjusted_slideronly_tmp["time"].max(),
    )
    axes2_DG_Plot.set_xticks(df_adjusted_slideronly_tmp["time"])
    axes2_DG_Plot.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    axes2_DG_Plot.tick_params(axis="x", rotation=90, labelsize=8)
    axes2_DG_Plot.tick_params(axis="x", rotation=90, labelsize=8)
    axes2_DG_Plot.tick_params(axis="y", labelsize=8)
    axes2_DG_Plot.set_title(
        "Dawlish Railway Line", loc="center", fontsize=12, fontweight="bold"
    )
    axes2_DG_Plot.set_ylabel(
        "No. of Overtopping Occurences (Per 10 Mins)", fontsize=10, labelpad=10
    )

    # Now plot our legend
    Randforest_high_confidence_scoring_metrics = mlines.Line2D(
        [],
        [],
        color="#00008B",
        marker="o",
        linestyle="None",
        markersize=10,
        label="High Confidence (> 80%)",
    )
    Randforest_medium_confidence_scoring_metrics = mlines.Line2D(
        [],
        [],
        color="#4682B4",
        marker="o",
        linestyle="None",
        markersize=10,
        label="Medium Confidence (50-80%)",
    )
    Randforest_low_confidence_scoring_metrics = mlines.Line2D(
        [],
        [],
        color="aqua",
        marker="o",
        linestyle="None",
        markersize=10,
        label="Low Confidence (< 50%)",
    )
    There_is_no_overtopping_recorded = mlines.Line2D(
        [],
        [],
        color="black",
        marker="x",
        linestyle="None",
        markersize=10,
        label="No Overtopping",
    )
    Upper_and_lower_iqr_dashed_lines = mlines.Line2D(
        [],
        [],
        color="black",
        linestyle="--",
        linewidth=1,
        label="Interquartile Range (25th & 75th)",
    )

    fig.legend(
        handles=[
            Randforest_high_confidence_scoring_metrics,
            Randforest_medium_confidence_scoring_metrics,
            Randforest_low_confidence_scoring_metrics,
            There_is_no_overtopping_recorded,
            Upper_and_lower_iqr_dashed_lines,
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=5,
        frameon=False,
    )

    plt.tight_layout()
    plt.show()


def on_submit_clicked(button):
    """Update overtopping graphs after inputting new variales values

    Args:
        b (Button): Button instance
    """

    df_adjusted = adjust_features(final_DawlishTwin_dataset)
    clear_output(wait=True)
    process_wave_overtopping(df_adjusted)
    display(
        Sig_wave_height_slider_output,
        Mean_Period_Slider,
        Cross_shore_wave_dir_slider,
        wind_speed_slider,
        Cross_shore_wind_dir_slider,
        freeboard_slider,
        submit_button,
    )


# Step 10, now we want to plot, for the processed block, what the changing Hs, freeboard, wind speed and direction was.
def save_penazance_combined_features_plot_with_overtopping(
    df, overtopping_times, output_path, start_date, end_date
):
    """Save combined features plot

    Args:
        df (Dataframe): Digital twin dataframe
        overtopping_times (Dataframe): Overtopping events dataframe
        output_path (string): Path to outputs folder
        start_date (string): Forecast start date
        end_date (string): Forecast end date
    """

    df = (
        df.set_index("time")
        .reindex(pd.date_range(start=start_date, end=end_date, freq="1H"))
        .interpolate(method="time")
        .reset_index()
    )
    df.rename(columns={"index": "time"}, inplace=True)
    fig, axs = plt.subplots(3, 1, figsize=(10, 9), dpi=300, sharex=True)
    overtopping_times_filtered = [
        time for time in overtopping_times if time in df["time"].values
    ]

    # Hs
    axs[0].plot(
        df["time"],
        df["Hs"],
        label="Significant Wave Height (Hs)",
        linewidth=1.5,
        color="blue",
    )
    axs[0].scatter(
        overtopping_times_filtered,
        df[df["time"].isin(overtopping_times_filtered)]["Hs"],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[0].set_ylabel("Hs (m)", fontsize=10)
    axs[0].set_ylim(0, 5)
    axs[0].legend(loc="upper left", fontsize=8)
    axs[0].grid(True)

    # Freeboard

    # Extract hourly water level data directly from the text file
    wl_data_hourly = extract_water_level_for_range(start_date, end_date)

    # Plot the Freeboard data (water level) from the text file
    axs[1].plot(
        wl_data_hourly.index,
        wl_data_hourly["water_level"],
        label="Freeboard (m)",
        linewidth=1.5,
        color="orange",
    )
    axs[1].scatter(
        overtopping_times_filtered,
        wl_data_hourly.loc[
            wl_data_hourly.index.isin(overtopping_times_filtered), "water_level"
        ],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[1].set_ylabel("Freeboard (m)", fontsize=10)
    axs[1].set_ylim(0, 6)
    axs[1].legend(loc="upper left", fontsize=8)
    axs[1].grid(True)

    # Wind Speed
    axs[2].plot(
        df["time"],
        df["Wind(m/s)"],
        label="Wind Speed (m/s)",
        linewidth=1.5,
        color="green",
    )
    axs[2].scatter(
        overtopping_times_filtered,
        df[df["time"].isin(overtopping_times_filtered)]["Wind(m/s)"],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[2].set_ylabel("Wind Speed (m/s)", fontsize=10)
    axs[2].set_ylim(0, 25)
    axs[2].set_xlabel("Time", fontsize=10)
    axs[2].legend(loc="upper left", fontsize=8)
    axs[2].grid(True)

    # Formatting
    for ax in axs:
        ax.set_xlim([start_date, end_date])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        ax.tick_params(axis="x", rotation=90, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)


def save_combined_features(final_DawlishTwin_dataset):
    """Save combined features

    Args:
        final_DawlishTwin_dataset (Dataframe): Digital twin dataframe
    """

    use_this_output_path_dawlish = os.environ.get("OUTPUT_PATH_DAWLISH")
    overtopping_times_dawlish = final_DawlishTwin_dataset[
        final_DawlishTwin_dataset["RF1_Final_Predictions"] == 1
    ]["time"]
    block_start_date = final_DawlishTwin_dataset["time"].min()
    block_end_date = final_DawlishTwin_dataset["time"].max()

    save_penazance_combined_features_plot_with_overtopping(
        final_DawlishTwin_dataset,
        overtopping_times_dawlish,
        use_this_output_path_dawlish,
        block_start_date,
        block_end_date,
    )


def get_overtopping_times_data(final_DawlishTwin_dataset, feature_name):
    """Get overtopping times data

    Args:
        final_DawlishTwin_dataset (Dataframe): Digital twin dataframe
        feature_name (string): Feature's name

    Returns:
        Dataframe: Overtopping events times dataframe
    """

    overtopping_times_dawlish = final_DawlishTwin_dataset[
        final_DawlishTwin_dataset["RF1_Final_Predictions"] == 1
    ]["time"]
    overtopping_times = pd.DataFrame()

    overtopping_times_filtered = [
        time
        for time in overtopping_times_dawlish
        if time in final_DawlishTwin_dataset["time"].values
    ]
    overtopping_times[feature_name] = final_DawlishTwin_dataset[
        final_DawlishTwin_dataset["time"].isin(overtopping_times_filtered)
    ][feature_name]
    overtopping_times["overtopping_time"] = overtopping_times_filtered
    return overtopping_times


def get_feature_and_overtopping_times_data(final_DawlishTwin_dataset, feature_name):
    """Get features and overtopping times data

    Args:
        final_DawlishTwin_dataset (Dataframe): Digital twin dataframe
        feature_name (string): Feature's name

    Returns:
        Dataframes: Interpolated feature and forecast-overtopping-events dataframes
    """

    overtopping_times_filtered = get_overtopping_times_data(
        final_DawlishTwin_dataset, feature_name
    )

    block_start_date = final_DawlishTwin_dataset["time"].min()
    block_end_date = final_DawlishTwin_dataset["time"].max()

    final_DawlishTwin_dataset = (
        final_DawlishTwin_dataset.set_index("time")
        .reindex(pd.date_range(start=block_start_date, end=block_end_date, freq="1H"))
        .interpolate(method="time")
        .reset_index()
    )
    final_DawlishTwin_dataset.rename(columns={"index": "time"}, inplace=True)
    return final_DawlishTwin_dataset, overtopping_times_filtered


def adjust_arrow_density(latitudes, longitudes, density_factor=12):
    """
    Adjusts the density of arrows to be plotted by returning slice objects.

    Args:
        latitudes (list): A list or array of latitude values.
        longitudes (list): A list or array of longitude values.
        density_factor (int, optional): The factor by which to reduce the
            density of arrows. Higher values result in fewer arrows. Defaults to 12.

    Returns:
        tuple: A tuple containing two slice objects, one for latitudes and
               one for longitudes. Each slice object specifies the step size
               for downsampling the corresponding array. The step size is
               calculated as the maximum of 1 and the length of the array
               divided by the density factor.
    """
    return (
        slice(None, None, max(1, len(latitudes) // density_factor)),
        slice(None, None, max(1, len(longitudes) // density_factor)),
    )


def plot_significant_wave_height():
    """Plot significant wave height"""

    # Step 11: Plot Hs geospatially and save to the figures folder
    send_here_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
    output_folder = os.environ.get("DAWLISH_OUTPUT_WAVES_FOLDER")
    state_file = os.environ.get("STATE_FILE_FOLDER")

    current_block_Met_office_final = datetime.now().strftime("%Y%m%d")
    print(f"Processing Block: {current_block_Met_office_final}")

    block_files = sorted(
        [
            os.path.join(send_here_wave_folder, f)
            for f in os.listdir(send_here_wave_folder)
            if f.endswith(".nc") and f"b{current_block_Met_office_final}" in f
        ]
    )

    if not block_files:
        print(
            f"No files found for Block {current_block_Met_office_final}. Falling back to the previous day's block."
        )
        current_block_Met_office_final = (
            datetime.strptime(current_block_Met_office_final, "%Y%m%d")
            - timedelta(days=1)
        ).strftime("%Y%m%d")
        block_files = sorted(
            [
                os.path.join(send_here_wave_folder, f)
                for f in os.listdir(send_here_wave_folder)
                if f.endswith(".nc") and f"b{current_block_Met_office_final}" in f
            ]
        )
        print(f"Retrying with Block: {current_block_Met_office_final}")

    if block_files:
        hs_list = []
        time_list = []

        for file in block_files:
            ds = xr.open_dataset(file)
            hs = ds[["VHM0", "VMDR"]]
            times = ds["time"].values
            hs_list.append(hs)
            time_list.extend(times)

        if hs_list:
            hs_combined_for_Dawlish_study_site = xr.concat(hs_list, dim="time")
            time_combined = np.array(time_list)

            # Coordinates (Southwest England)
            lat_bound_Dawlish_Seawall = [49.5, 51.5]
            lon_bounds_Dawlish_Seawall = [-6.0, -2.0]
            hs_combined_for_Dawlish_study_site["longitude"] = xr.where(
                hs_combined_for_Dawlish_study_site["longitude"] > 180,
                hs_combined_for_Dawlish_study_site["longitude"] - 360,
                hs_combined_for_Dawlish_study_site["longitude"],
            )
            hs_southwest = hs_combined_for_Dawlish_study_site.sel(
                latitude=slice(
                    lat_bound_Dawlish_Seawall[0], lat_bound_Dawlish_Seawall[1]
                ),
                longitude=slice(
                    lon_bounds_Dawlish_Seawall[0], lon_bounds_Dawlish_Seawall[1]
                ),
            )

            dawlish_lat_seawall = 50.56757
            dawlish_lon_seawall = -3.42424
            penzance_lat_seawall = 50.1186
            penzance_lon_seawall = -5.5373

            for time_idx, time_value in enumerate(time_combined):
                if time_idx % 6 == 0:
                    hs_frame_digital_twin = hs_southwest.sel(time=time_value)

                    time_label = pd.Timestamp(time_value).strftime("%Y-%m-%d %H:%M:%S")
                    plt.figure(figsize=(10, 8))

                    z_data = hs_frame_digital_twin["VHM0"].squeeze().values
                    if z_data.ndim > 2:
                        z_data = z_data[0]

                    wave_dir_frame = hs_frame_digital_twin["VMDR"]
                    wave_dir = wave_dir_frame.values

                    longitudes = hs_frame_digital_twin["longitude"].values
                    latitudes = hs_frame_digital_twin["latitude"].values
                    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)

                    U = -np.sin(np.deg2rad(wave_dir))
                    V = -np.cos(np.deg2rad(wave_dir))

                    land_margin_mask = ~np.isnan(z_data) & (z_data > 0.2)
                    U = np.where(land_margin_mask, U, np.nan)
                    V = np.where(land_margin_mask, V, np.nan)

                    skip = adjust_arrow_density(
                        latitudes, longitudes, density_factor=12
                    )

                    mako_cmap = sns.color_palette("mako", as_cmap=True)
                    norm = Normalize(vmin=0, vmax=11)

                    contour = plt.contourf(
                        longitudes,
                        latitudes,
                        z_data,
                        levels=np.linspace(0, 11, 21),
                        cmap=mako_cmap,
                        norm=norm,
                    )
                    cbar = plt.colorbar(
                        contour, label="Significant Wave Height (Hs) [m]"
                    )
                    cbar.set_ticks(np.linspace(0, 11, 12))

                    plt.quiver(
                        lon_grid[skip],
                        lat_grid[skip],
                        U[skip],
                        V[skip],
                        color="white",
                        scale=50,
                        width=0.002,
                    )

                    # Colour markers
                    plt.scatter(
                        dawlish_lon_seawall,
                        dawlish_lat_seawall,
                        color="red",
                        label="Dawlish",
                        s=50,
                        marker="o",
                    )
                    plt.scatter(
                        penzance_lon_seawall,
                        penzance_lat_seawall,
                        color="red",
                        label="Penzance",
                        s=50,
                        marker="s",
                    )

                    legend_elements = [
                        Line2D(
                            [0],
                            [0],
                            color="white",
                            lw=1,
                            marker=">",
                            markersize=10,
                            label="Wave Direction (°)",
                            markerfacecolor="white",
                        ),
                        Line2D(
                            [0],
                            [0],
                            marker="o",
                            color="red",
                            markersize=8,
                            label="Dawlish",
                            linestyle="None",
                        ),
                        Line2D(
                            [0],
                            [0],
                            marker="s",
                            color="red",
                            markersize=8,
                            label="Penzance",
                            linestyle="None",
                        ),
                    ]
                    plt.legend(handles=legend_elements, loc="upper left")

                    plt.title(
                        f"Significant Wave Height (Hs)\nBlock: {current_block_Met_office_final}, Time: {time_label}"
                    )
                    plt.xlabel("Longitude")
                    plt.ylabel("Latitude")
                    plt.grid(False)

                    output_file = os.path.join(
                        output_folder,
                        f'hs_wave_direction_plot_block_{current_block_Met_office_final}_time_{time_label.replace(":", "_")}.png',
                    )
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    print(f"Saved plot for time {time_label} to {output_file}")

    with open(state_file, "w") as f:
        f.write(current_block_Met_office_final)
    print(f"Updated state file to block: {current_block_Met_office_final}")


def generate_overtopping_graphs():
    """Generate overtopping graphs"""

    global final_DawlishTwin_dataset
    final_DawlishTwin_dataset = get_digital_twin_dataset(datetime.now().date())
    load_models(SPLASH_DIGITAL_TWIN_models_folder)

    process_wave_overtopping(final_DawlishTwin_dataset)
    display(
        Sig_wave_height_slider_output,
        Mean_Period_Slider,
        Cross_shore_wave_dir_slider,
        wind_speed_slider,
        Cross_shore_wind_dir_slider,
        freeboard_slider,
        submit_button,
    )
    submit_button.on_click(on_submit_clicked)

    save_combined_features(final_DawlishTwin_dataset)
    # plot_significant_wave_height()


# generate_overtopping_graphs()
