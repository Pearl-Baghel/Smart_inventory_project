from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import List

import pandas as pd

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except Exception:
    PROPHET_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

SALES_CSV = PROCESSED_DIR / "sales.csv"
OUT_WEEKLY_TOTALS = PROCESSED_DIR / "weekly_item_totals.csv"
OUT_FORECAST = PROCESSED_DIR / "weekly_forecast.csv"

FORECAST_HORIZON_WEEKS = 4
MOVING_AVG_WINDOW_WEEKS = 4
CROSTON_ALPHA = 0.3
INTERMITTENT_ZERO_RATIO_THRESHOLD = 0.40
MIN_WEEKS_FOR_PROPHET = 8


@dataclass
class ForecastResult:
    item: str
    week_end_date: pd.Timestamp
    forecast_qty: int
    method: str


def _ensure_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path}. Run src/raw_to_sales_clean.py and src/ingest_validate.py first."
        )


def _week_end_sunday(d: pd.Series) -> pd.Series:
    return d.dt.to_period("W-SUN").dt.end_time.dt.normalize()


def round_up_qty(value: float) -> int:
    return int(ceil(max(0, float(value))))


def build_weekly_totals(sales: pd.DataFrame) -> pd.DataFrame:
    sales = sales.copy()

    required_cols = {"date", "item", "quantity sold"}
    missing = required_cols - set(sales.columns)
    if missing:
        raise ValueError(f"sales.csv missing columns: {sorted(missing)}. Found: {list(sales.columns)}")

    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    sales["quantity sold"] = pd.to_numeric(sales["quantity sold"], errors="coerce")

    if sales["date"].isna().any():
        bad_rows = sales[sales["date"].isna()].index.tolist()[:10]
        raise ValueError(f"Invalid dates found in sales.csv. Example rows: {bad_rows}")

    if sales["quantity sold"].isna().any():
        bad_rows = sales[sales["quantity sold"].isna()].index.tolist()[:10]
        raise ValueError(f"Invalid quantity sold values found in sales.csv. Example rows: {bad_rows}")

    sales["week_end_date"] = _week_end_sunday(sales["date"])

    weekly = (
        sales.groupby(["item", "week_end_date"], as_index=False)["quantity sold"]
        .sum()
        .rename(columns={"quantity sold": "weekly_qty"})
        .sort_values(["item", "week_end_date"])
        .reset_index(drop=True)
    )
    weekly["weekly_qty"] = weekly["weekly_qty"].apply(round_up_qty)
    return weekly


def build_complete_weekly_grid(weekly: pd.DataFrame) -> pd.DataFrame:
    all_items = weekly["item"].unique()
    min_date = weekly["week_end_date"].min()
    max_date = weekly["week_end_date"].max()

    all_weeks = pd.date_range(start=min_date, end=max_date, freq="W-SUN")

    grid = pd.MultiIndex.from_product(
        [all_items, all_weeks],
        names=["item", "week_end_date"]
    ).to_frame(index=False)

    full_weekly = grid.merge(weekly, on=["item", "week_end_date"], how="left")
    full_weekly["weekly_qty"] = full_weekly["weekly_qty"].fillna(0).apply(round_up_qty)

    return full_weekly.sort_values(["item", "week_end_date"]).reset_index(drop=True)


def moving_average_forecast(series: pd.Series, horizon: int, window_weeks: int) -> List[int]:
    window = min(window_weeks, len(series))
    baseline = float(series.tail(window).mean()) if len(series) > 0 else 0.0
    return [round_up_qty(baseline)] * horizon


def croston_forecast(series: pd.Series, horizon: int, alpha: float = 0.3) -> List[int]:
    values = series.astype(float).tolist()

    demand = []
    intervals = []
    interval = 1

    for x in values:
        if x > 0:
            demand.append(x)
            intervals.append(interval)
            interval = 1
        else:
            interval += 1

    if not demand:
        return [0] * horizon

    z = demand[0]
    p = intervals[0]

    for i in range(1, len(demand)):
        z = z + alpha * (demand[i] - z)
        p = p + alpha * (intervals[i] - p)

    forecast = z / p if p != 0 else 0.0
    return [round_up_qty(forecast)] * horizon


def prophet_forecast(df_item: pd.DataFrame, horizon: int) -> List[int]:
    model_df = df_item.rename(columns={"week_end_date": "ds", "weekly_qty": "y"}).copy()
    model_df["ds"] = pd.to_datetime(model_df["ds"])
    model_df["y"] = pd.to_numeric(model_df["y"], errors="coerce").fillna(0)

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False
    )
    model.fit(model_df)

    future = model.make_future_dataframe(periods=horizon, freq="W")
    forecast = model.predict(future)
    future_rows = forecast.tail(horizon)["yhat"].clip(lower=0)

    return [round_up_qty(x) for x in future_rows.tolist()]


def forecast_per_item(full_weekly: pd.DataFrame) -> pd.DataFrame:
    results: List[ForecastResult] = []

    for item, df_item in full_weekly.groupby("item"):
        df_item = df_item.sort_values("week_end_date").reset_index(drop=True)
        series = df_item["weekly_qty"].astype(float)
        last_week = df_item["week_end_date"].iloc[-1]

        zero_ratio = float((series == 0).mean())
        future_weeks = pd.date_range(
            start=last_week + pd.Timedelta(days=7),
            periods=FORECAST_HORIZON_WEEKS,
            freq="W-SUN",
        )

        if zero_ratio >= INTERMITTENT_ZERO_RATIO_THRESHOLD:
            forecast_values = croston_forecast(series, FORECAST_HORIZON_WEEKS, alpha=CROSTON_ALPHA)
            method = "Croston"
        else:
            if PROPHET_AVAILABLE and len(df_item) >= MIN_WEEKS_FOR_PROPHET:
                try:
                    prophet_input = df_item[["week_end_date", "weekly_qty"]].copy()
                    forecast_values = prophet_forecast(prophet_input, FORECAST_HORIZON_WEEKS)
                    method = "Prophet"
                except Exception:
                    forecast_values = moving_average_forecast(series, FORECAST_HORIZON_WEEKS, MOVING_AVG_WINDOW_WEEKS)
                    method = "Moving Average"
            else:
                forecast_values = moving_average_forecast(series, FORECAST_HORIZON_WEEKS, MOVING_AVG_WINDOW_WEEKS)
                method = "Moving Average"

        for week_date, qty in zip(future_weeks, forecast_values):
            results.append(
                ForecastResult(
                    item=item,
                    week_end_date=week_date,
                    forecast_qty=round_up_qty(qty),
                    method=method
                )
            )

    return pd.DataFrame([r.__dict__ for r in results]).sort_values(
        ["item", "week_end_date"]
    ).reset_index(drop=True)


def save_outputs(weekly_totals: pd.DataFrame, forecast: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    weekly_totals.to_csv(OUT_WEEKLY_TOTALS, index=False)
    forecast.to_csv(OUT_FORECAST, index=False)

    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = EXPORTS_DIR / f"run_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    weekly_totals.to_csv(run_dir / "weekly_item_totals.csv", index=False)
    forecast.to_csv(run_dir / "weekly_forecast.csv", index=False)

    print("\nWeekly totals and forecast generated successfully.")
    print(f"Weekly totals saved to: {OUT_WEEKLY_TOTALS}")
    print(f"Forecast saved to: {OUT_FORECAST}")
    print(f"Snapshot saved to: {run_dir}")

    if not PROPHET_AVAILABLE:
        print("\nNote: Prophet is not installed, so regular-demand items used Moving Average fallback.")
        print("To install Prophet, run: pip install prophet")


def main() -> None:
    _ensure_file_exists(SALES_CSV)

    sales = pd.read_csv(SALES_CSV)
    weekly_totals = build_weekly_totals(sales)

    if weekly_totals.empty:
        raise ValueError("No weekly totals were created. Check sales.csv.")

    full_weekly = build_complete_weekly_grid(weekly_totals)
    forecast = forecast_per_item(full_weekly)

    save_outputs(full_weekly, forecast)


if __name__ == "__main__":
    main()
    