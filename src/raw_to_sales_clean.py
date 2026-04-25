from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "Pearl Data.xlsx"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "sales.csv"


ITEM_NAME_MAP = {
    "Chickpea Meal Plate": "Chickpea Meal Plate",
    "Red KidneyBean Plate": "Red KidneyBean Plate",
    "Paneer Meal Plate": "Paneer Meal Plate",
    "Lentil Soup": "Lentil soup",
    "Sweet Yogurt": "Strawberry yogurt",
    "Pani Puri Eat Here": "Pani Puri 5 Balls",
    "Pani Puri ToGo": "Pani Puri 12 Balls",
    "Spiced Lemonade": "Pepsi Lemonade",
    "Water": "Water",
}

PRICE_MAP = {
    "Chickpea Meal Plate": 8.99,
    "Red KidneyBean Plate": 8.99,
    "Paneer Meal Plate": 8.99,
    "Lentil soup": 7.99,
    "Strawberry yogurt": 4.99,
    "Pani Puri 5 Balls": 3.00,
    "Pani Puri 12 Balls": 6.00,
    "Pepsi Lemonade": 4.00,
    "Water": 1.00,
}

SATURDAY_MARKET = "Mt Sac Farmers Market"
SUNDAY_MARKET = "Tustin Farmers Market"


def assign_market_location(date_series: pd.Series) -> pd.Series:
    weekday_num = pd.to_datetime(date_series).dt.dayofweek
    return weekday_num.map({5: SATURDAY_MARKET, 6: SUNDAY_MARKET}).fillna("Unknown")


def main() -> None:
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    df = pd.read_excel(RAW_FILE)
    df.columns = [str(c).strip() for c in df.columns]

    if "Date" not in df.columns:
        raise ValueError(f"'Date' column not found in raw file. Found: {list(df.columns)}")

    item_columns = [col for col in ITEM_NAME_MAP if col in df.columns]
    if not item_columns:
        raise ValueError(
            "No expected item columns found in raw file. "
            f"Found columns: {list(df.columns)}"
        )

    long_df = df.melt(
        id_vars=["Date"],
        value_vars=item_columns,
        var_name="item",
        value_name="quantity sold",
    )

    long_df["quantity sold"] = pd.to_numeric(long_df["quantity sold"], errors="coerce").fillna(0)
    long_df = long_df[long_df["quantity sold"] > 0].copy()

    long_df["date"] = pd.to_datetime(long_df["Date"], errors="coerce").dt.date
    if long_df["date"].isna().any():
        bad_rows = long_df[long_df["date"].isna()].index.tolist()[:10]
        raise ValueError(f"Invalid dates found in raw file. Example row indexes: {bad_rows}")

    long_df["item"] = long_df["item"].replace(ITEM_NAME_MAP)
    long_df["price"] = long_df["item"].map(PRICE_MAP).fillna(0.0)
    long_df["market location"] = assign_market_location(pd.to_datetime(long_df["date"]))

    sales = long_df[[
        "date",
        "item",
        "quantity sold",
        "price",
        "market location",
    ]].sort_values(["date", "item"]).reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT_FILE, index=False)

    print("Sales cleaned successfully.")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Rows written: {len(sales)}")
    print("\nMarket location assigned automatically from weekday:")
    print(f"Saturday -> {SATURDAY_MARKET}")
    print(f"Sunday   -> {SUNDAY_MARKET}")


if __name__ == "__main__":
    main()