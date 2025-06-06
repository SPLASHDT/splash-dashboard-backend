# SPDX-FileCopyrightText: © 2025 National Oceanography Centre and University of Plymouth

# SPDX-License-Identifier: MIT

"""SPLASH Digital Twin Penzance"""

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

from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from datetime import datetime, timedelta
import joblib
from IPython.display import display, clear_output
import matplotlib.lines as mlines

import ipywidgets as widgets
from IPython.display import display
import matplotlib.ticker as ticker
import os
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from matplotlib.colors import Normalize
import os
from dotenv import load_dotenv
import utils


utils.loadConfigFile()
# Step 2: Downloading and concatenating our dataset.

# We extract from thee file paths (wave, wind, water level(wl)). NB: we have a state file so if we do not have the proceeding data we proceed using the nearest time.
SPLASH_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
SPLASH_wind_folder = os.environ.get("MET_OFFICE_WIND_FOLDER")
wl_file = os.environ.get("PENZANCE_WATER_LEVEL_FILE")
state_file = os.environ.get("STATE_FILE")

# We must extract from the lat/long coordinates for Penzance wave buoy.
Penzance_wave_buoy_LATITUDE = float(os.environ.get("PENZANCE_WAVE_BUOY_LATITUDE"))
Penzance_wave_buoy_LONGITUDE = float(os.environ.get("PENZANCE_WAVE_BUOY_LONGITUDE"))

SPLASH_Digital_Twin_models_folder = os.environ.get("PENZANCE_MODELS_FOLDER")

models = {"RF1": {}, "RF2": {}, "RF3": {}, "RF4": {"Regressor": {}}}

# Step 4: Slider Adjustments, this allows us to play around with altering the forecast data (for fun) and see if it changes the predicitons in anyway.

penzance_slider_style_layout = {"description_width": "150px"}
slider_layout_design_with_digital_twin = widgets.Layout(width="400px")
significant_wave_height_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Hs (%):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)
mean_period_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Tm (%):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)
shore_wave_direction_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=0,
    max=360,
    step=1,
    description="ShoreWaveDir (°):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)
wind_speed_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Wind (m/s) (%):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)
shore_wind_direction_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=0,
    max=360,
    step=1,
    description="ShoreWindDir (°):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)
freeboard_slider_SPLASH = widgets.FloatSlider(
    value=0,
    min=-100,
    max=100,
    step=1,
    description="Freeboard (%):",
    style=penzance_slider_style_layout,
    layout=slider_layout_design_with_digital_twin,
)

submit_button = widgets.Button(description="Submit")
use_our_previous_SPLASH_rf1_rf2 = None
use_our_previous_SPLASH_rf3_rf4 = None
previous_rf1_confidences = None
previous_rf3_confidences = None
df = pd.DataFrame()
start_time = datetime.now()


def setInputFolderPaths(option: str = "penzance"):
    """Set input folder paths

    Args:
        option (str, optional): Dataset's option name. Defaults to "penzance".
    """

    global SPLASH_wave_folder, SPLASH_wind_folder, wl_file
    (
        met_office_wave_folder,
        met_office_wind_folder,
        water_level_file,
        penzance_water_level_file,
    ) = utils.getLocationDataPaths(option)
    SPLASH_wave_folder = met_office_wave_folder
    SPLASH_wind_folder = met_office_wind_folder
    wl_file = penzance_water_level_file


def get_wave_files(block_date):
    """Get wave files

    Args:
        block_date (string): String representing date

    Returns:
        Array: Array of files names
    """

    Met_office_wave_files = []
    for file_name in os.listdir(SPLASH_wave_folder):
        if file_name.startswith(
            f"metoffice_wave_amm15_NWS_WAV_b{block_date.strftime('%Y%m%d')}"
        ):  # this is our unique code (date) identifier
            Met_office_wave_files.append(os.path.join(SPLASH_wave_folder, file_name))
    return sorted(Met_office_wave_files)


def get_wind_file(template, folder, date):
    """Get wind file

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


def extract_wave_data(Met_office_wave_files):
    """Extract the wave data after we know the speficic location on interest

    Args:
        Met_office_wave_files (Array): Array of file names

    Raises:
        ValueError: Error's description

    Returns:
        Dataframe: Mean wave data values
    """

    wave_data = []
    for file_path in Met_office_wave_files:
        Penzance_ds_wave = xr.open_dataset(file_path)
        ds_filtered_wave = Penzance_ds_wave.sel(
            latitude=Penzance_wave_buoy_LATITUDE,
            longitude=Penzance_wave_buoy_LONGITUDE,
            method="nearest",
        )
        Penzance_df_wave = (
            ds_filtered_wave[["time", "VHM0", "VTM02", "VMDR"]]
            .to_dataframe()
            .reset_index()
        )
        Penzance_df_wave = Penzance_df_wave.rename(
            columns={
                "time": "datetime",
                "VHM0": "Hs",
                "VTM02": "Tm",
                "VMDR": "shoreWaveDir",
            }
        )  # All this is saying is our variable names in the dataset differe from the model training names
        Penzance_df_wave = Penzance_df_wave[["datetime", "Hs", "Tm", "shoreWaveDir"]]
        Penzance_df_wave["datetime"] = pd.to_datetime(Penzance_df_wave["datetime"])
        wave_data.append(Penzance_df_wave)
    if not wave_data:
        raise ValueError("There is no wave data for this block.")
    Penzance_combined_wave = pd.concat(wave_data, ignore_index=True)
    return Penzance_combined_wave.set_index("datetime").resample("3H").mean()


def extract_wind_data(wind_file):
    """Extract the wind speed and direction files.

    Args:
        wind_file (string): Wind file path

    Raises:
        ValueError: Error's description

    Returns:
        Dataframe: Penzance wind dataframe
    """

    data = []
    grbs = pygrib.open(wind_file)

    for grb in grbs:
        if grb.level == 10:
            values = grb.values
            lats, lons = grb.latlons()
            converted_lons = np.where(lons > 180, lons - 360, lons)
            distances = np.sqrt(
                (lats - Penzance_wave_buoy_LATITUDE) ** 2
                + (converted_lons - Penzance_wave_buoy_LONGITUDE) ** 2
            )
            min_dist_index = np.unravel_index(distances.argmin(), distances.shape)
            value = values[min_dist_index]
            data_date = grb.dataDate
            data_time = grb.dataTime
            Met_office_forecast_time = grb.forecastTime
            init_datetime = datetime.strptime(
                f"{data_date:08d}{data_time:04d}", "%Y%m%d%H%M"
            )
            Met_office_forecast_datetime = init_datetime + timedelta(
                hours=Met_office_forecast_time
            )

            if Met_office_forecast_time <= 54 or Met_office_forecast_time % 3 == 0:
                data.append({"datetime": Met_office_forecast_datetime, "value": value})

    grbs.close()

    if not data:
        raise ValueError("There is no available wind data.")

    Penzance_df_wind = pd.DataFrame(data)
    Penzance_df_wind["datetime"] = pd.to_datetime(Penzance_df_wind["datetime"])
    Penzance_df_wind = Penzance_df_wind.drop_duplicates(subset="datetime").set_index(
        "datetime"
    )

    return Penzance_df_wind


def extract_water_level_data():
    """Extract the wl data (this is the easiest, its in one combined text file)

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
    water_level["datetime"] = pd.to_datetime(
        water_level["date"] + " " + water_level["time"], format="%d/%m/%Y %H:%M"
    )
    water_level = water_level.set_index("datetime")[["water_level"]]
    return water_level.resample("3H").interpolate()


def extract_hourly_water_level_data(start_date, end_date):
    """Extract hourly water level data

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
    water_level["datetime"] = pd.to_datetime(
        water_level["date"] + " " + water_level["time"], format="%d/%m/%Y %H:%M"
    )
    water_level = water_level.rename(
        columns={"datetime": "Time", "water_level": "tidal_level"}
    )
    water_level = water_level.set_index("Time")[["tidal_level"]]

    water_level = water_level.loc[start_date:end_date]
    return water_level.asfreq("1H").interpolate()


def process_block(block_date):
    """Concatenate our data into a big dataset

    Args:
        block_date (Date): Forecast date

    Returns:
        Dataframe: Combined dataframe which holds all variables data
    """

    try:
        wave_files = get_wave_files(block_date)
        wind_speed_file = get_wind_file(
            "agl_wind-speed-{}", SPLASH_wind_folder, block_date
        )
        wind_direction_file = get_wind_file(
            "agl_wind-direction-{}", SPLASH_wind_folder, block_date
        )

        with ThreadPoolExecutor() as executor:
            wave_future_at_Penzance = executor.submit(extract_wave_data, wave_files)
            wind_speed_future_at_Penzance = executor.submit(
                extract_wind_data, wind_speed_file
            )
            wind_direction_future = executor.submit(
                extract_wind_data, wind_direction_file
            )
            water_level_future = executor.submit(extract_water_level_data)

            wave_data = wave_future_at_Penzance.result()
            wind_speed_data = wind_speed_future_at_Penzance.result().rename(
                columns={"value": "Wind Speed"}
            )
            wind_direction_data = wind_direction_future.result().rename(
                columns={"value": "Wind Direction"}
            )
            water_level_data = water_level_future.result()

        Our_finalised_combined_data = wave_data.resample("1H").mean()
        wind_speed_data = wind_speed_data.resample("1H").mean()
        wind_direction_data = wind_direction_data.resample("1H").mean()
        water_level_data = water_level_data.resample("1H").interpolate()
        Our_finalised_combined_data = Our_finalised_combined_data.join(
            [wind_speed_data, wind_direction_data, water_level_data], how="left"
        )
        first_54_hours = Our_finalised_combined_data.iloc[:54]
        after_54_hours = Our_finalised_combined_data.iloc[54:].resample("3H").asfreq()
        after_54_hours = after_54_hours.join(
            wind_speed_data, on="datetime", how="left", rsuffix="_wind"
        ).interpolate()
        after_54_hours = after_54_hours.join(
            wind_direction_data, on="datetime", how="left", rsuffix="_dir"
        ).interpolate()
        after_54_hours = after_54_hours.join(
            water_level_data, on="datetime", how="left", rsuffix="_wl"
        ).interpolate()
        Our_finalised_combined_data = pd.concat([first_54_hours, after_54_hours])
        Our_finalised_combined_data.reset_index(inplace=True)

        start_date = Our_finalised_combined_data["datetime"].min()
        end_date = Our_finalised_combined_data["datetime"].max()
        print(f"Processed Block: Start Date = {start_date}, End Date = {end_date}")

        # Save the current block state
        with open(state_file, "w") as file:
            file.write(block_date.strftime("%Y-%m-%d"))

        return Our_finalised_combined_data

    except ValueError as e:
        print(f"Error: {e}")
        print(
            "No data available for today's block. Automatically using the previous day's block..."
        )
        previous_block_date = block_date - timedelta(days=1)
        return process_block(previous_block_date)


def get_next_block(block_date):
    """Get the next block date, this is the tricky bit, the code should recognise the date on the files and then logically proceed to the next date but this should be verified

    Args:
        block_date (Date): Forecast date

    Returns:
        Date: Today's date or last block's date
    """

    today_date = block_date
    if os.path.exists(state_file):
        with open(state_file, "r") as file:
            last_date = datetime.strptime(file.read().strip(), "%Y-%m-%d").date()
        if last_date < today_date:
            return today_date  # Process today's block
        return last_date  # Resume from the last block
    else:
        return today_date  # Start with today's date


def get_digital_twin_dataset(start_date):
    """Get digital twin dataset

    Args:
        start_date (Date): Forecast start date

    Raises:
        ValueError: Error's description

    Returns:
        Dataframe, Date, Date: Digital twin dataframe, inital forecast date, last block's date
    """

    # This is our file names, these are all the variables we need to make our predicitons.
    # Ensure we get the next block to process
    start_date_block_tmp = get_next_block(start_date)
    Penzance_block_data_remember = process_block(start_date_block_tmp)

    # Check if the data is successfully loaded
    if Penzance_block_data_remember is not None:
        Penzance_block_data_remember = Penzance_block_data_remember.rename(
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
        df = Penzance_block_data_remember.copy()
        start_time_tmp = df["time"].iloc[0]
    else:
        raise ValueError(
            "No data could be processed for the current or previous blocks."
        )

    return df, start_time_tmp, start_date_block_tmp


def load_model_files(SPLASH_Digital_Twin_models_folder):
    """Load our SPLASH models, all these models have individually been tuned, regularised (if needed) with optimised threshold adjustments for harminising the F1 score, if you require the code for each model, just ask.

    Args:
        SPLASH_Digital_Twin_models_folder (string): Digital twin models folder
    """

    for file_name in os.listdir(SPLASH_Digital_Twin_models_folder):
        if "RF1" in file_name:
            if "T24" in file_name:
                models["RF1"]["T24"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T48" in file_name:
                models["RF1"]["T48"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T72" in file_name:
                models["RF1"]["T72"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
        elif "RF2" in file_name:
            if "T24" in file_name:
                models["RF2"]["T24"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T48" in file_name:
                models["RF2"]["T48"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T72" in file_name:
                models["RF2"]["T72"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
        elif "RF3" in file_name:
            if "T24" in file_name:
                models["RF3"]["T24"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T48" in file_name:
                models["RF3"]["T48"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T72" in file_name:
                models["RF3"]["T72"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
        elif "RF4" in file_name:
            if "T24" in file_name:
                models["RF4"]["Regressor"]["T24"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T48" in file_name:
                models["RF4"]["Regressor"]["T48"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )
            elif "T72" in file_name:
                models["RF4"]["Regressor"]["T72"] = joblib.load(
                    os.path.join(SPLASH_Digital_Twin_models_folder, file_name)
                )


# Step 5: Calculate the Confidence of our model when it predicts whether overtopping happens. Please note, we apply gini to assign confidence for our binary, this confidence is not for our regreession model which would typically use MSE
def get_confidence_color(confidence):
    """Get colour according to confidence value

    Args:
        confidence (float): Confidence value

    Returns:
        string: Colour's name
    """

    try:
        confidence = float(confidence)
        if confidence > 0.8:
            return "#00008B"
        elif 0.5 < confidence <= 0.8:
            return "#4682B4"
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

    Penzance_adjusted_note = df.copy()
    Penzance_adjusted_note["Hs"] *= (
        1 + significant_wave_height_slider_SPLASH.value / 100
    )
    Penzance_adjusted_note["Tm"] *= 1 + mean_period_slider_SPLASH.value / 100
    Penzance_adjusted_note["shoreWaveDir"] = shore_wave_direction_slider_SPLASH.value
    Penzance_adjusted_note["Wind(m/s)"] *= 1 + wind_speed_slider_SPLASH.value / 100
    Penzance_adjusted_note["shoreWindDir"] = shore_wind_direction_slider_SPLASH.value
    Penzance_adjusted_note["Freeboard"] *= 1 + freeboard_slider_SPLASH.value / 100
    return Penzance_adjusted_note


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

    Penzance_adjusted_note = df.copy()
    Penzance_adjusted_note["Hs"] *= 1 + sig_wave_height / 100
    Penzance_adjusted_note["Tm"] *= 1 + mean_wave_period / 100
    Penzance_adjusted_note["shoreWaveDir"] = mean_wave_dir
    Penzance_adjusted_note["Wind(m/s)"] *= 1 + wind_speed / 100
    Penzance_adjusted_note["shoreWindDir"] = wind_direction
    Penzance_adjusted_note["Freeboard"] *= 1 + freeboard / 100
    return Penzance_adjusted_note


def adjust_freeboard_only(df, freeboard):
    """Adjust feeboard value only

    Args:
        df (Dataframe): Initial digital twin dataframe
        freeboard (_type_): Freeboard value in percentage

    Returns:
        Dataframe: Dataframe with adjusted features values
    """

    Penzance_adjusted_note = df.copy()
    Penzance_adjusted_note["tidal_level"] *= 1 + freeboard / 100
    return Penzance_adjusted_note


def revise_rf1_prediction(rf1_prediction, hs_value):
    """Revise rf1 prediction

    Args:
        rf1_prediction (integer): Prediction value
        hs_value (float): Significant wave height value

    Returns:
        integer: Final prediction value
    """
    if rf1_prediction == 1 and hs_value < 0.84:
        return 0
    if rf1_prediction == 0 and (
        (2.08 <= hs_value <= 2.17) or (2.32 <= hs_value <= 2.37)
    ):
        return 1
    return rf1_prediction


def revise_rf1_prediction_wind(rf1_prediction, wind_speed):
    """Revise rf1 prediction wind

    Args:
        rf1_prediction (integer): Prediction value
        wind_speed (float): Wind speed value

    Returns:
        integer: Final prediction value
    """

    if rf1_prediction == 1 and wind_speed < 2.8:
        return 0
    return rf1_prediction


def revise_rf1_prediction_crossshorewind(rf1_prediction, crossshore_wind_dir):
    """Revise rf1 prediction crossshorewind

    Args:
        rf1_prediction (integer): Predicition value
        crossshore_wind_dir (float): Wind direction value

    Returns:
        integer: Final prediction value
    """

    if rf1_prediction == 1 and crossshore_wind_dir > 300:
        return 0
    return rf1_prediction


def revise_rf1_prediction_crossshorewave(rf1_prediction, crossshore_wave):
    """Revise rf1 prediction crossshorewave

    Args:
        rf1_prediction (integer): Prediction value
        crossshore_wave (float): Mean wave direction value

    Returns:
        integer: Final prediction value
    """

    if rf1_prediction == 0 and crossshore_wave in [98, 99, 100, 102, 103, 104, 107]:
        return 1
    return rf1_prediction


def revise_rf1_prediction_freeboard(rf1_prediction, freeboard_value):
    """Revise rf1 prediction freeboard

    Args:
        rf1_prediction (integer): Prediction value
        freeboard_value (float): Freeboard value

    Returns:
        integer: Final prediction value
    """

    if rf1_prediction == 1 and (
        (5.367 <= freeboard_value <= 5.491)
        or (5.561 <= freeboard_value <= 5.647)
        or (3.615 <= freeboard_value <= 3.692)
        or (5.677 <= freeboard_value <= 5.788)
    ):
        return 0
    return rf1_prediction


def add_selected_model_col(dt_df, start_time_tmp):
    """Add selected model column to main dataframe

    Args:
        dt_df (Dataframe): Digital twin dataframe
        start_time_tmp (Date): Forecast start date

    Returns:
        Dataframe: Updated digital twin dataframe
    """

    # Step 6: Now we must get our models to acutally predict. We have 4 questions: 1. overtopping occurence rig 1 (yes/no), overtopping frequency at rig 1 (n = ?), overtopping occurence at rig 2 (yes/no), overtopping freuqency at rig 2 (n= ?)

    if "Selected_Model" not in dt_df.columns:
        print("Assigning 'Selected_Model' column...")

        def select_model_based_on_time(row):
            Met_Office_forecast_time_difference = (
                row["time"] - start_time_tmp
            ).total_seconds() / 3600
            if Met_Office_forecast_time_difference < 24:  # earliest pretrained model
                return "T24"
            elif 24 <= Met_Office_forecast_time_difference <= 48:  # mid model
                return "T48"
            else:
                return "T72"  # later model

        dt_df["Selected_Model"] = dt_df.apply(select_model_based_on_time, axis=1)
    return dt_df


def process_wave_overtopping(df_adjusted, start_time):
    """Process wave overtopping

    Args:
        df_adjusted (Dataframe): Main dataframe with adjusted wave and atmospheric variables
        start_time (Date): Forecast start date

    Returns:
        Dataframes: First location and second location wave-overtopping-events dataframes
    """

    global use_our_previous_SPLASH_rf1_rf2, use_our_previous_SPLASH_rf3_rf4, previous_rf1_confidences, previous_rf3_confidences
    Met_office_time_stamps = df_adjusted["time"].dropna()
    Our_overtopping_counts_rig1_rf1_rf2 = []
    Our_overtopping_counts_rig2_rf3_rf4 = []
    rf1_confidences = []
    rf3_confidences = []

    rf1_final_predictions = []

    for idx, row in df_adjusted.iterrows():
        forecast_hour = (row["time"] - start_time).total_seconds() / 3600

        # Only predict at hourly intervals up to 54h, then switch to 3-hourly
        if forecast_hour > 54 and forecast_hour % 3 != 0:
            continue

        selected_model = row["Selected_Model"]
        input_data = (
            row[["Hs", "Tm", "shoreWaveDir", "Wind(m/s)", "shoreWindDir", "Freeboard"]]
            .to_frame()
            .T
        )

        Digital_Twin_rf1_model = models["RF1"][selected_model]
        rf1_prediction = Digital_Twin_rf1_model.predict(input_data)[0]
        rf1_confidence = Digital_Twin_rf1_model.predict_proba(input_data)[0][1]
        rf1_confidences.append(rf1_confidence)

        # Apply threshold criteria
        final_rf1_prediction_use = revise_rf1_prediction(rf1_prediction, row["Hs"])
        final_rf1_prediction_use = revise_rf1_prediction_wind(
            final_rf1_prediction_use, row["Wind(m/s)"]
        )
        final_rf1_prediction_use = revise_rf1_prediction_crossshorewind(
            final_rf1_prediction_use, row["shoreWindDir"]
        )
        final_rf1_prediction_use = revise_rf1_prediction_crossshorewave(
            final_rf1_prediction_use, row["shoreWaveDir"]
        )
        final_rf1_prediction_use = revise_rf1_prediction_freeboard(
            final_rf1_prediction_use, row["Freeboard"]
        )

        # Store final predictions for both dots and further processing
        rf1_final_predictions.append(final_rf1_prediction_use)

        # Get overtopping counts based on RF1 prediction
        if final_rf1_prediction_use == 0:
            Our_overtopping_counts_rig1_rf1_rf2.append(0)
        else:
            Digital_Twin_rf2_model = models["RF2"][selected_model]
            final_rf2_prediction_use = Digital_Twin_rf2_model.predict(input_data)[0]
            Our_overtopping_counts_rig1_rf1_rf2.append(final_rf2_prediction_use)

        if final_rf1_prediction_use == 1:
            rf3_model = models["RF3"][selected_model]
            rf4_regressor = models["RF4"]["Regressor"][selected_model]
            rf3_prediction = rf3_model.predict(input_data)[0]
            rf3_confidence = rf3_model.predict_proba(input_data)[0][1]
            rf3_confidences.append(rf3_confidence)

            if rf3_prediction == 0:
                Our_overtopping_counts_rig2_rf3_rf4.append(0)
            else:
                rf4_prediction = rf4_regressor.predict(input_data)[0]
                Our_overtopping_counts_rig2_rf3_rf4.append(
                    min(rf4_prediction, final_rf2_prediction_use)
                )
        else:
            Our_overtopping_counts_rig2_rf3_rf4.append(0)
            rf3_confidences.append(0)

    # Assign final RF1 predictions to the dataframe
    df_adjusted["RF1_Final_Predictions"] = rf1_final_predictions

    data_rf1_rf2 = pd.DataFrame(
        {
            "Time": Met_office_time_stamps,
            "Overtopping Count": Our_overtopping_counts_rig1_rf1_rf2,
            "Confidence": rf1_confidences,
        }
    )

    data_rf3_rf4 = pd.DataFrame(
        {
            "Time": Met_office_time_stamps,
            "Overtopping Count": Our_overtopping_counts_rig2_rf3_rf4,
            "Confidence": rf3_confidences,
        }
    )

    # plot_overtopping_graphs(df_adjusted, Met_office_time_stamps, Our_overtopping_counts_rig1_rf1_rf2, Our_overtopping_counts_rig2_rf3_rf4, rf1_confidences, rf3_confidences)

    return data_rf1_rf2, data_rf3_rf4


def plot_overtopping_graphs(
    df_adjusted,
    Met_office_time_stamps_df,
    Our_overtopping_counts_rig1_rf1_rf2,
    Our_overtopping_counts_rig2_rf3_rf4,
    rf1_confidences,
    rf3_confidences,
):
    """Plot overtopping graphs

    Args:
        df_adjusted (Dataframe): Main dataframe with adjusted wave and atmospheric variables
        Met_office_time_stamps_df (Dataframe): Time stamps dataframe
        Our_overtopping_counts_rig1_rf1_rf2 (List): Overtopping counts list of first location
        Our_overtopping_counts_rig2_rf3_rf4 (List): Overtopping counts list of second location
        rf1_confidences (List): Confidence values list of overtopping events prediction for first location
        rf3_confidences (List): Confidence values list of overtopping events prediction for second location
    """

    global use_our_previous_SPLASH_rf1_rf2, use_our_previous_SPLASH_rf3_rf4, previous_rf1_confidences, previous_rf3_confidences

    clear_output(wait=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), dpi=300)
    ax1.set_title(
        "Penzance, Seawall crest", fontsize=10, fontweight="bold"
    )  # may want to change the names of both locations, not sure just lest it at this.
    ax2.set_title("Penzance, Seawall crest (sheltered)", fontsize=10, fontweight="bold")

    # Fix selected timestamps for plotting (first 54h hourly, then 3-hourly)
    selected_timestamps = []
    for timestamp in df_adjusted["time"]:
        forecast_hour = (timestamp - start_time).total_seconds() / 3600
        if forecast_hour <= 54 or forecast_hour % 3 == 0:
            selected_timestamps.append(timestamp)

    df_adjusted = df_adjusted[df_adjusted["time"].isin(selected_timestamps)]

    # Rig 1 (Seawall Crest)
    for i, count in enumerate(Our_overtopping_counts_rig1_rf1_rf2):
        time_point = Met_office_time_stamps_df.iloc[i]

        if time_point not in selected_timestamps:
            continue  # Skip timestamps outside valid intervals

        if count == 0:
            ax1.scatter(
                time_point, count, marker="x", color="black", s=100, linewidths=1.5
            )
        else:
            color = get_confidence_color(rf1_confidences[i])
            ax1.scatter(
                time_point,
                count,
                marker="o",
                color=color,
                s=75,
                edgecolor="black",
                linewidth=1,
            )

    ax1.axhline(y=6, color="black", linestyle="--", linewidth=1, label="25% IQR (6)")
    ax1.axhline(y=54, color="black", linestyle="--", linewidth=1, label="75% IQR (54)")
    ax1.set_ylim(-10, 120)
    ax1.set_xlabel("Time", fontsize=10)
    ax1.set_ylabel("No. of Overtopping Occurrences (Per 10 Mins)", fontsize=10)
    ax1.set_xticks(selected_timestamps)
    ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
    ax1.tick_params(axis="x", rotation=90, labelsize=8)
    ax1.tick_params(axis="y", labelsize=8)

    # Rig 2 (Seawall Crest Sheltered)
    for i, count in enumerate(Our_overtopping_counts_rig2_rf3_rf4):
        time_point = Met_office_time_stamps_df.iloc[i]

        if time_point not in selected_timestamps:
            continue  # Skip timestamps outside valid intervals

        if count == 0:
            ax2.scatter(
                time_point, count, marker="x", color="black", s=100, linewidths=1.5
            )
        else:
            color = get_confidence_color(rf3_confidences[i])
            ax2.scatter(
                time_point,
                count,
                marker="o",
                color=color,
                s=75,
                edgecolor="black",
                linewidth=1,
            )

    ax2.axhline(y=2, color="black", linestyle="--", linewidth=1, label="25% IQR (2)")
    ax2.axhline(y=9, color="black", linestyle="--", linewidth=1, label="75% IQR (9)")
    ax2.set_ylim(-5, 120)
    ax2.set_xlabel("Time", fontsize=10)
    ax2.set_ylabel("No. of Overtopping Occurrences (Per 10 Mins)", fontsize=10)
    ax2.set_xticks(selected_timestamps)
    ax2.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
    ax2.tick_params(axis="x", rotation=90, labelsize=8)
    ax2.tick_params(axis="y", labelsize=8)

    # Confidence Legends
    Digital_twin_has_high_confidence = mlines.Line2D(
        [],
        [],
        color="#00008B",
        marker="o",
        linestyle="None",
        markersize=8,
        label="High Confidence (> 80%)",
    )
    Digital_twin_has_medium_confidence = mlines.Line2D(
        [],
        [],
        color="#4682B4",
        marker="o",
        linestyle="None",
        markersize=8,
        label="Medium Confidence (50-80%)",
    )
    Digital_twin_has_low_confidence = mlines.Line2D(
        [],
        [],
        color="aqua",
        marker="o",
        linestyle="None",
        markersize=8,
        label="Low Confidence (< 50%)",
    )
    No_overtopping_recorded = mlines.Line2D(
        [],
        [],
        color="black",
        marker="x",
        linestyle="None",
        markersize=8,
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
            Digital_twin_has_high_confidence,
            Digital_twin_has_medium_confidence,
            Digital_twin_has_low_confidence,
            No_overtopping_recorded,
            Upper_and_lower_iqr_dashed_lines,
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=5,
        frameon=False,
        fontsize=8,
    )

    plt.tight_layout()
    plt.show()

    use_our_previous_SPLASH_rf1_rf2 = Our_overtopping_counts_rig1_rf1_rf2
    use_our_previous_SPLASH_rf3_rf4 = Our_overtopping_counts_rig2_rf3_rf4
    previous_rf1_confidences = rf1_confidences[:]
    previous_rf3_confidences = rf3_confidences[:]

    display(
        significant_wave_height_slider_SPLASH,
        mean_period_slider_SPLASH,
        shore_wave_direction_slider_SPLASH,
        wind_speed_slider_SPLASH,
        shore_wind_direction_slider_SPLASH,
        freeboard_slider_SPLASH,
        submit_button,
    )


def on_submit_clicked(b):
    """Update overtopping graphs after inputting new variales values

    Args:
        b (Button): Button instance
    """

    df_adjusted = adjust_features(df)
    process_wave_overtopping(df_adjusted, start_time)


# step 8: plot now the subplot figures
def save_combined_features_plot(
    df, hourly_freeboard, send_to_this_output_path_folder, overtopping_times
):
    """Save combined features plot

    Args:
        df (Dataframe): Digital twin dataframe
        hourly_freeboard (Dataframe): Hourly freeboard dataframe
        send_to_this_output_path_folder (string): Path to outputs folder
        overtopping_times (Dataframe): Overtopping events times dataframe
    """

    fig, axs = plt.subplots(3, 1, figsize=(8, 8), dpi=300, sharex=True)

    # Hs
    axs[0].plot(
        df["time"],
        df["Hs"],
        label="Significant Wave Height (Hs)",
        linewidth=1.5,
        color="blue",
    )
    axs[0].scatter(
        overtopping_times,
        df.loc[df["time"].isin(overtopping_times), "Hs"],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[0].set_ylabel("Hs (m)", fontsize=10)
    axs[0].set_ylim(0, 5)
    axs[0].legend(loc="upper left", fontsize=8)
    axs[0].grid(True)

    # Freeboard
    axs[1].plot(
        hourly_freeboard["datetime"],
        hourly_freeboard["water_level"],
        label="Freeboard (Hourly)",
        linewidth=1.5,
        color="orange",
    )
    axs[1].scatter(
        overtopping_times,
        hourly_freeboard.loc[
            hourly_freeboard["datetime"].isin(overtopping_times), "water_level"
        ],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[1].set_ylabel("Freeboard (m)", fontsize=10)
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
        overtopping_times,
        df.loc[df["time"].isin(overtopping_times), "Wind(m/s)"],
        color="red",
        label="Overtopping Event",
        zorder=5,
    )
    axs[2].set_ylabel("Wind Speed (m/s)", fontsize=10)
    axs[2].set_ylim(0, 25)
    axs[2].legend(loc="upper left", fontsize=8)
    axs[2].grid(True)
    axs[2].set_xlabel("Time", fontsize=10)

    for ax in axs:
        ax.xaxis.set_major_formatter(
            plt.matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M")
        )
        ax.tick_params(axis="x", rotation=90, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

    plt.tight_layout()
    plt.savefig(send_to_this_output_path_folder, dpi=300)
    plt.close(fig)


def combine_features(df):
    """Combine_features

    Args:
        df (Dataframe): Digital twin dataframe
    """

    hourly_freeboard = pd.read_csv(
        wl_file,
        sep=r"\s+",
        header=None,
        skiprows=2,
        names=["date", "time", "water_level"],
        engine="python",
    )
    hourly_freeboard["datetime"] = pd.to_datetime(
        hourly_freeboard["date"] + " " + hourly_freeboard["time"],
        format="%d/%m/%Y %H:%M",
    )
    hourly_freeboard = hourly_freeboard.set_index("datetime")[["water_level"]]
    date_range = pd.date_range(start=df["time"].min(), end=df["time"].max(), freq="1h")
    hourly_freeboard = (
        hourly_freeboard.reindex(date_range).interpolate(method="time").reset_index()
    )
    hourly_freeboard.rename(columns={"index": "datetime"}, inplace=True)
    df = get_interpolated_feature_data(df)
    overtopping_times = df[df["RF1_Final_Predictions"] == 1]["time"]
    send_to_this_output_path_folder = os.environ.get("OUTPUT_PATH_PENZANCE")

    save_combined_features_plot(
        df, hourly_freeboard, send_to_this_output_path_folder, overtopping_times
    )


def get_overtopping_times_data(final_PenzanceTwin_dataset, feature_name):
    """Get overtopping times data

    Args:
        final_PenzanceTwin_dataset (Dataframe): Digital twin dataframe
        feature_name (string): Variable's name

    Returns:
        _type_: Forecast overtopping events times dataframe
    """

    overtopping_times_penzance = final_PenzanceTwin_dataset[
        final_PenzanceTwin_dataset["RF1_Final_Predictions"] == 1
    ]["time"]
    overtopping_times = pd.DataFrame()

    overtopping_times_filtered = [
        time
        for time in overtopping_times_penzance
        if time in final_PenzanceTwin_dataset["time"].values
    ]
    overtopping_times[feature_name] = final_PenzanceTwin_dataset[
        final_PenzanceTwin_dataset["time"].isin(overtopping_times_filtered)
    ][feature_name]
    overtopping_times["overtopping_time"] = overtopping_times_filtered
    return overtopping_times


def get_interpolated_feature_data(final_PenzanceTwin_dataset):
    """Get feature data

    Args:
        final_PenzanceTwin_dataset (Dataframe): Digital twin dataframe

    Returns:
        Dataframe: Interpolated feature dataframe
    """

    final_PenzanceTwin_dataset["time"] = pd.to_datetime(
        final_PenzanceTwin_dataset["time"]
    )
    final_PenzanceTwin_dataset.set_index("time", inplace=True)
    final_PenzanceTwin_dataset["Hs"] = final_PenzanceTwin_dataset["Hs"].interpolate(
        method="time"
    )
    final_PenzanceTwin_dataset["Wind(m/s)"] = final_PenzanceTwin_dataset[
        "Wind(m/s)"
    ].interpolate(method="time")
    final_PenzanceTwin_dataset.reset_index(inplace=True)

    return final_PenzanceTwin_dataset


def get_feature_and_overtopping_times_data(final_PenzanceTwin_dataset, feature_name):
    """Get feature and overtopping times data

    Args:
        final_PenzanceTwin_dataset (Dataframe): Digital twin dataframe
        feature_name (string): Feature's name

    Returns:
        Dataframes: Interpolated feature and forecast-overtopping-events dataframes
    """

    overtopping_times_filtered = get_overtopping_times_data(
        final_PenzanceTwin_dataset, feature_name
    )

    final_PenzanceTwin_dataset = get_interpolated_feature_data(
        final_PenzanceTwin_dataset
    )
    return final_PenzanceTwin_dataset, overtopping_times_filtered


def plot_significant_wave_height(start_date_block):
    """Plot significant wave height graphs

    Args:
        start_date_block (Date): Forecast start date
    """

    # Step 9. Now we also want to plot Hs and wave direction geospatially and save to figures folder.

    send_here_wave_folder = os.environ.get("MET_OFFICE_WAVE_FOLDER")
    output_folder = os.environ.get("PENZANCE_OUTPUT_WAVES_FOLDER")

    current_block = start_date_block.strftime("%Y%m%d")
    print(f"Processing Block: {current_block}")

    block_files = sorted(
        [
            os.path.join(send_here_wave_folder, f)
            for f in os.listdir(send_here_wave_folder)
            if f.endswith(".nc") and f"b{current_block}" in f
        ]
    )

    if not block_files:
        print(
            f"No files found for Block {current_block}. Using the previous day's block..."
        )
        current_block = (
            datetime.strptime(current_block, "%Y%m%d") - timedelta(days=1)
        ).strftime("%Y%m%d")
        block_files = sorted(
            [
                os.path.join(send_here_wave_folder, f)
                for f in os.listdir(send_here_wave_folder)
                if f.endswith(".nc") and f"b{current_block}" in f
            ]
        )
        print(f"Restarting with Block: {current_block}")
        print(f"Files in Block {current_block}: {block_files}")

    if block_files:
        hs_list = []
        time_list = []

        for file in block_files:
            ds = xr.open_dataset(file)
            hs_vmdr = ds[["VHM0", "VMDR"]]
            times = ds["time"].values
            hs_list.append(hs_vmdr)
            time_list.extend(times)

        if hs_list:
            hs_combined_for_Penzance_study_site = xr.concat(hs_list, dim="time")
            time_combined = np.array(time_list)

            # Coordinates (Southwest England)
            lat_bound_Penzance_Seawall = [49.5, 51.5]
            lon_bounds = [-6.0, -2.0]
            hs_combined_for_Penzance_study_site["longitude"] = xr.where(
                hs_combined_for_Penzance_study_site["longitude"] > 180,
                hs_combined_for_Penzance_study_site["longitude"] - 360,
                hs_combined_for_Penzance_study_site["longitude"],
            )
            hs_southwest = hs_combined_for_Penzance_study_site.sel(
                latitude=slice(
                    lat_bound_Penzance_Seawall[0], lat_bound_Penzance_Seawall[1]
                ),
                longitude=slice(lon_bounds[0], lon_bounds[1]),
            )

            # Coordinates for Penzance (study site)
            penzance_lat_seawall = 50.08874
            penzance_lon_seawall = -5.52474
            dawlish_lat_seawall = 50.56757
            dawlish_lon_seawall = -3.42424

            for time_idx, time_value in enumerate(time_combined):
                if time_idx % 6 == 0:  # Plot every 6 hours
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

                    magnitude = np.sqrt(U**2 + V**2)
                    U_normalised = U / magnitude
                    V_normalised = V / magnitude

                    land_margin_mask = ~np.isnan(z_data) & (z_data > 0.2)
                    U_normalised = np.where(land_margin_mask, U_normalised, np.nan)
                    V_normalised = np.where(land_margin_mask, V_normalised, np.nan)

                    density_factor = 12
                    skip = (
                        slice(None, None, max(1, len(latitudes) // density_factor)),
                        slice(None, None, max(1, len(longitudes) // density_factor)),
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
                        U_normalised[skip],
                        V_normalised[skip],
                        color="white",
                        scale=50,
                        width=0.002,
                        label="_nolegend_",
                    )

                    plt.scatter(
                        penzance_lon_seawall,
                        penzance_lat_seawall,
                        color="red",
                        s=50,
                        marker="s",
                        label="Penzance",
                        zorder=5,
                    )
                    plt.scatter(
                        dawlish_lon_seawall,
                        dawlish_lat_seawall,
                        color="red",
                        s=50,
                        label="Dawlish",
                        zorder=5,
                    )

                    legend_handles = [
                        plt.Line2D(
                            [],
                            [],
                            color="white",
                            marker="$\u2192$",
                            markersize=10,
                            linestyle="None",
                            label="Wave Direction (°)",
                        ),
                        plt.Line2D(
                            [],
                            [],
                            color="red",
                            marker="s",
                            markersize=10,
                            linestyle="None",
                            label="Penzance",
                        ),
                        plt.Line2D(
                            [],
                            [],
                            color="red",
                            marker="o",
                            markersize=10,
                            linestyle="None",
                            label="Dawlish",
                        ),
                    ]
                    plt.legend(handles=legend_handles, loc="upper left")

                    plt.title(
                        f"Significant Wave Height (Hs)\nBlock: {current_block}, Time: {time_label}"
                    )
                    plt.xlabel("Longitude")
                    plt.ylabel("Latitude")
                    plt.grid(False)

                    output_file = os.path.join(
                        output_folder,
                        f'hs_wave_direction_plot_block_{current_block}_time_{time_label.replace(":", "_")}.png',
                    )
                    plt.savefig(output_file, dpi=300)
                    plt.close()
                    print(f"Saved plot for time {time_label} to {output_file}")


def generate_overtopping_graphs():
    """Generate overtopping events graphs, features line plots and significant-wave-height contour plots"""

    global df, start_time
    df, start_time, start_date_block = get_digital_twin_dataset(datetime.now().date())
    load_model_files(SPLASH_Digital_Twin_models_folder)
    df = add_selected_model_col(df, start_time)

    submit_button.on_click(
        lambda b: process_wave_overtopping(adjust_features(df), start_time)
    )
    submit_button.on_click(on_submit_clicked)
    display(
        significant_wave_height_slider_SPLASH,
        mean_period_slider_SPLASH,
        shore_wave_direction_slider_SPLASH,
        wind_speed_slider_SPLASH,
        shore_wind_direction_slider_SPLASH,
        freeboard_slider_SPLASH,
        submit_button,
    )
    process_wave_overtopping(df, start_time)

    combine_features(df)
    # plot_significant_wave_height(start_date_block)


# generate_overtopping_graphs()
