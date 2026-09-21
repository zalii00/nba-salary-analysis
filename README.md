# Raw data

Not committed to this repo because of size (GitHub rejects files over 100 MB).

`scripts/build_dataset.py` needs one file here:

- **`PlayerStatistics.csv`** (~390 MB) from the Kaggle dataset
  [NBA Dataset: Box Scores and Stats (1947–Today)](https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores).
  Download the dataset and place `PlayerStatistics.csv` in this folder.

No other raw files are used. The dataset's other files (games, team stats, schedules,
play-by-play) aren't needed to reproduce the analysis.

The Kaggle dataset is updated over time, so a later download may differ slightly from
the version used for the published results. The committed files in `data/` are the exact
inputs to the notebooks.
