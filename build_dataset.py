"""
Build the analysis dataset for "Does NBA Salary Predict Performance?" (2025-26).

Steps
  1. Aggregate raw box scores (Kaggle PlayerStatistics.csv) into one row per player
     for the 2025-26 regular season, keeping players with 10+ games played.
  2. Clean player names in both sources (accents, punctuation, Jr./II/III suffixes).
  3. Inner-join performance to salaries on the cleaned name.

Usage (from the repo root)
  python scripts/build_dataset.py                 # reproduces the published 456-player file
  python scripts/build_dataset.py --fix-aliases   # also recovers 4 players lost to name mismatches

Step 1 needs data/raw/PlayerStatistics.csv (~390 MB, not in the repo; see data/raw/README.md).
If it's missing, the script skips step 1 and uses the committed performance file.
"""
import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw" / "PlayerStatistics.csv"

SEASON_START, SEASON_END = "2025-10-01", "2026-07-01"
MIN_GAMES = 10

# Names that clean differently in the two sources. Off by default so the
# output matches the published analysis exactly.
ALIASES = {
    "ronald holland": "ron holland",
    "egor demin": "egor dmin",  # salary source has a Cyrillic "ё" that strips to nothing
    "hugo gonzalez": "hugo gonzalez pena",
    "gg jackson": "gregory jackson",
}

STAT_COLS = ["points", "assists", "reboundsTotal", "steals", "blocks", "turnovers",
             "fieldGoalsMade", "fieldGoalsAttempted", "threePointersMade",
             "threePointersAttempted", "freeThrowsMade", "freeThrowsAttempted"]


PERF_COLS = ["personId", "playerName", "gamesPlayed", "minutes"] + STAT_COLS + [
    "pointsPerGame", "assistsPerGame", "reboundsTotalPerGame", "stealsPerGame",
    "blocksPerGame", "turnoversPerGame", "minutesPerGame", "fieldGoalPct",
    "threePointPct", "freeThrowPct", "productionPerGame", "name_clean"]


def clean_name(name: str) -> str:
    n = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    n = n.lower().replace(".", "").replace("'", "")
    n = re.sub(r"\s+", " ", n).strip()
    return re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", n)


def build_performance() -> pd.DataFrame:
    usecols = ["firstName", "lastName", "personId", "gameId", "gameDateTimeEst",
               "gameType", "numMinutes"] + STAT_COLS
    ps = pd.read_csv(RAW, usecols=usecols, low_memory=False)
    ps["date"] = pd.to_datetime(ps["gameDateTimeEst"], errors="coerce", utc=True)
    ps["minutes"] = pd.to_numeric(ps["numMinutes"], errors="coerce")
    season = ps[(ps["date"] >= SEASON_START) & (ps["date"] < SEASON_END)
                & (ps["gameType"] == "Regular Season")
                & ps["minutes"].notna()]  # a recorded minutes value = appeared in the game

    g = season.groupby("personId")
    perf = g[STAT_COLS].sum()
    perf["minutes"] = g["minutes"].sum().round(1)
    perf["gamesPlayed"] = g["gameId"].nunique()
    last = g[["firstName", "lastName"]].last()
    perf["playerName"] = last["firstName"].str.strip() + " " + last["lastName"].str.strip()
    perf = perf[perf["gamesPlayed"] >= MIN_GAMES].reset_index()

    gp = perf["gamesPlayed"]
    for c, new in [("points", "pointsPerGame"), ("assists", "assistsPerGame"),
                   ("reboundsTotal", "reboundsTotalPerGame"), ("steals", "stealsPerGame"),
                   ("blocks", "blocksPerGame"), ("turnovers", "turnoversPerGame"),
                   ("minutes", "minutesPerGame")]:
        perf[new] = (perf[c] / gp).round(1 if c == "minutes" else 2)
    perf["fieldGoalPct"] = (perf["fieldGoalsMade"] / perf["fieldGoalsAttempted"]).round(3)
    perf["threePointPct"] = (perf["threePointersMade"] / perf["threePointersAttempted"]).round(3)
    perf["freeThrowPct"] = (perf["freeThrowsMade"] / perf["freeThrowsAttempted"]).round(3)
    perf["productionPerGame"] = (perf["pointsPerGame"] + perf["reboundsTotalPerGame"]
                                 + perf["assistsPerGame"] + perf["stealsPerGame"]
                                 + perf["blocksPerGame"] - perf["turnoversPerGame"])
    perf["productionPerGame"] = perf["productionPerGame"].round(2)
    perf["name_clean"] = perf["playerName"].map(clean_name)
    return perf[PERF_COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-aliases", action="store_true",
                    help="recover players whose names differ between sources")
    args = ap.parse_args()

    if RAW.exists():
        perf = build_performance()
        perf.to_csv(DATA / "performance_2025_26_cleaned.csv", index=False)
        print(f"Built performance table from raw box scores: {len(perf)} players")
    else:
        perf = pd.read_csv(DATA / "performance_2025_26_cleaned.csv")
        print(f"{RAW.name} not found; using committed performance file ({len(perf)} players)")

    sal = pd.read_csv(DATA / "salaries_2025_26.csv")
    sal["name_clean"] = sal["player"].map(clean_name)

    key = perf["name_clean"].replace(ALIASES) if args.fix_aliases else perf["name_clean"]
    merged = (perf.assign(join_key=key)
                  .merge(sal.drop(columns="name_clean").assign(join_key=sal["name_clean"]),
                         on="join_key", how="inner")
                  .drop(columns="join_key"))

    unmatched = perf.loc[~key.isin(sal["name_clean"]), "playerName"]
    print(f"Merged: {len(merged)} players ({len(unmatched)} performance rows without a salary match)")

    out = DATA / ("nba_salary_performance_2025_26_aliased.csv" if args.fix_aliases
                  else "nba_salary_performance_2025_26.csv")
    merged.to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
