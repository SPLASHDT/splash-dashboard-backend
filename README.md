<p>
    <img src="assets/imgs/splash_logo.png">
    <img src="assets/imgs/splash_title.png" hspace="15" >
</p>

## DIGITAL APPROACHES TO PREDICT WAVE OVERTOPPING HAZARDS

### Advancing current understanding on wave-related coastal hazards

With sea level rise accelerating and weather extremes becoming increasingly stronger, tools to help climate adaptation of coastal communities are of paramount importance. SPLASH provides an overtopping tool that will act as forecast model directly helping coastal communities mitigate effects of this coastal hazard, and ultimately, guiding new climate adaptation strategies.

The model has been developed at the University of Plymouth Coastal Processes Research Group (CPRG) as part of the SPLASH project. The project was part of the Twinning Capability for the Natural Environment (TWINE) programme, designed to harness the potential of digital twinning technology to transform environmental science.

SPLASH digital twin is based on AI models trained using field measurements of wave overtopping. The model is updated once a day and uses Met Office wave and wind data as input, as well as predicted water level. This tool provides overtopping forecast 5 days ahead for Dawlish and Penzance, and allows the user to modify wind and wave input variables to test the sensitivity of wave overtopping.

# Documentation

More details about Splash project can be found in the following link: https://www.plymouth.ac.uk/research/coastal-processes/splash-project

# Dashboard Backend

Backend which implements RESTful APIs to support functionalities of Splash dashboard.

# Run backend API on any environment

1. Set a system environment variable temporarily using the following command in you terminal. Make sure you do not close terminal while running the backend API. For example, to run dashboard locally, set SPLASH_ENV environment variable to _**local**_ value. For staging and production environments use _**staging**_ and _**production**_ values.

```bash
% export SPLASH_ENV="local"
```
To check system environment variable value, run the following command:

```bash
% echo $SPLASH_ENV
```

2. Download synthetic water level, wave and wind datasets from Zenodo platform following this link [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15394753.svg)](https://doi.org/10.5281/zenodo.15394753). Go to **Files** section and click on **Download All** or **Download** button. This action will download a **data.zip** folder.

3. Unzip and copy **data** folder inside root folder. The **data** folder structure must be like this:

```bash
    |__data
        |__data_inputs
            |__water
            |__wave
            |   |_no_overtopping
            |   |_storm_bert
            |__wind
                |_no_overtopping
                |_storm_bert
```
4. Download Dawlish and Penzance models from the next repository https://github.com/SPLASHDT/splash_models. Copy **DWL_RF_models** and **PNZ_RF_models** folders inside **data_inputs** folder. Rename **DWL_RF_models** to **dawlish_models** and **PNZ_RF_models** to **penzance_models**. The **data** folder structure must look like this:

```bash
    |__data
        |__data_inputs
            |__dawlish_models
            |__penzance_models
            |__water
            |__wave
            |   |_no_overtopping
            |   |_storm_bert
            |__wind
                |_no_overtopping
                |_storm_bert

```

5. Create **data_outputs** folder inside **data** folder, add **dawlish** and **penzance** folders inside **data_outputs**. Add **all_plots** and **waves** folders inside **dawlish** and **penzance** folders. The **data** folder estructure must look like this:

```bash
    |__data
        |__data_inputs
        |   |__dawlish_models
        |   |__penzance_models
        |   |__water
        |   |__wave
        |   |   |_no_overtopping
        |   |   |_storm_bert
        |   |__wind
        |        |_no_overtopping
        |        |_storm_bert
        |__data_outputs
            |__dawlish
            |   |__all_plots
            |   |__waves
            |__penzance
                |__all_plots
                |__waves

```

6. To run backend API, run main.py script using the following command:

```bash
    % python3 main.py
```

# Digital Object Identifier

[![DOI](https://zenodo.org/badge/920796017.svg)](https://doi.org/10.5281/zenodo.15281624)