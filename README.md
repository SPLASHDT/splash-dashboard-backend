# splash-dashboard-backend
Backend which implements RESTful APIs to support functionalities of Splash dashboard.

# Run backend on local environment
1. Set a system environment variable temporarily using the following command in you terminal. Make sure you do not close terminal while running the backend API:

```bash
% export SPLASH_ENV="local"
```
To check system environment variable value, run the following command:

```bash
% echo $SPLASH_ENV
```

2. Create other_assets, data_inputs, models, dawlish and penzance, water_level, wave_level, wind, data_outputs, dawlish, penzance, all_plots, waves folders following the next directory tree structure.

```bash
    |__other-assets
        |__data_inputs
        |   |__models
        |   |   |__dawlish
        |   |   |__penzance
        |   |__water_level
        |   |__wave_level
        |   |__wind
        |__data_outputs
            |__dawlish
            |   |__all_plots
            |   |__waves
            |__penzance
                |__all_plots
                |__waves

```

3. Add Dawlish models files to other-assets/data_inputs/modesl/dawlish and Penzance models files to other-assets/data_inputs/modesl/penzance folder.
4. Add water level datasets to other-assets/data_inputs/water_level folder.
5. Add wave level datasets to other-assets/data_inputs/wave_level folder.
6. Add wind datasets to other-assets/data_inputs/wind folder.
7. To run backend API locally, run main.py script using the following command:

```bash
    % python3 main.py
```

