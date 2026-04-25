from __future__ import annotations

from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

FORECAST_CSV = PROCESSED_DIR / "weekly_forecast.csv"
BOM_CSV = PROCESSED_DIR / "recipes_bom.csv"
SUB_BOM_CSV = PROCESSED_DIR / "subcomponents_bom.csv"
INVENTORY_CSV = PROCESSED_DIR / "inventory_snapshot.csv"

OUT_REQUIREMENTS = PROCESSED_DIR / "requirements_components.csv"
OUT_RECOMMENDED = PROCESSED_DIR / "recommended_purchases.csv"

SAFETY_STOCK_PCT_INGREDIENTS = 0.15
SAFETY_STOCK_PCT_PACKAGING = 0.10
PLAN_MODE = "next_only"


def _ensure_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def _normalize_str(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def _fail(msg: str) -> None:
    raise SystemExit(f"\nERROR: {msg}\n")


def round_up_qty(value: float) -> int:
    return int(ceil(max(0, float(value))))


def load_inputs() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _ensure_exists(FORECAST_CSV)
    _ensure_exists(BOM_CSV)
    _ensure_exists(SUB_BOM_CSV)
    _ensure_exists(INVENTORY_CSV)

    forecast = pd.read_csv(FORECAST_CSV)
    bom = pd.read_csv(BOM_CSV)
    sub_bom = pd.read_csv(SUB_BOM_CSV)
    inventory = pd.read_csv(INVENTORY_CSV)

    return forecast, bom, sub_bom, inventory


def validate_inputs(
    forecast: pd.DataFrame,
    bom: pd.DataFrame,
    sub_bom: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    req_f = {"item", "week_end_date", "forecast_qty"}
    req_b = {"item", "component", "quantity per unit", "kg", "component_type"}
    req_s = {
        "subcomponent",
        "ingredient",
        "qty_per_subcomponent",
        "sub_unit_of_measurement",
        "ingredient_unit_of_measuresurment",
    }
    req_i = {"snapshot_date", "component", "on_hand_qty", "unit_of_measurement", "component_type"}

    if not req_f.issubset(set(forecast.columns)):
        _fail(f"weekly_forecast.csv must include {sorted(req_f)}. Found: {list(forecast.columns)}")

    if not req_b.issubset(set(bom.columns)):
        _fail(f"recipes_bom.csv must include {sorted(req_b)}. Found: {list(bom.columns)}")

    if not req_s.issubset(set(sub_bom.columns)):
        _fail(f"subcomponents_bom.csv must include {sorted(req_s)}. Found: {list(sub_bom.columns)}")

    if not req_i.issubset(set(inventory.columns)):
        _fail(f"inventory_snapshot.csv must include {sorted(req_i)}. Found: {list(inventory.columns)}")


def choose_planning_weeks(forecast: pd.DataFrame) -> pd.DataFrame:
    forecast = forecast.copy()
    forecast["week_end_date"] = pd.to_datetime(forecast["week_end_date"], errors="coerce")

    if forecast["week_end_date"].isna().any():
        _fail("weekly_forecast.csv contains invalid week_end_date values.")

    if PLAN_MODE == "next_only":
        next_week = forecast["week_end_date"].min()
        forecast = forecast[forecast["week_end_date"] == next_week].copy()

    return forecast


def compute_requirements_components(
    forecast: pd.DataFrame,
    bom: pd.DataFrame,
    sub_bom: pd.DataFrame
) -> pd.DataFrame:
    forecast = forecast.copy()
    bom = bom.copy()
    sub_bom = sub_bom.copy()

    forecast["item"] = _normalize_str(forecast["item"])

    bom["item"] = _normalize_str(bom["item"])
    bom["component"] = _normalize_str(bom["component"])
    bom["component_type"] = _normalize_str(bom["component_type"]).str.lower()
    bom["kg"] = _normalize_str(bom["kg"]).str.lower()

    sub_bom["subcomponent"] = _normalize_str(sub_bom["subcomponent"])
    sub_bom["ingredient"] = _normalize_str(sub_bom["ingredient"])
    sub_bom["sub_unit_of_measurement"] = _normalize_str(sub_bom["sub_unit_of_measurement"]).str.lower()
    sub_bom["ingredient_unit_of_measuresurment"] = _normalize_str(
        sub_bom["ingredient_unit_of_measuresurment"]
    ).str.lower()

    forecast["forecast_qty"] = pd.to_numeric(forecast["forecast_qty"], errors="coerce")
    bom["quantity per unit"] = pd.to_numeric(bom["quantity per unit"], errors="coerce")
    sub_bom["qty_per_subcomponent"] = pd.to_numeric(sub_bom["qty_per_subcomponent"], errors="coerce")

    if forecast["forecast_qty"].isna().any():
        _fail("weekly_forecast.csv has invalid forecast_qty values.")
    if bom["quantity per unit"].isna().any():
        _fail("recipes_bom.csv has invalid 'quantity per unit' values.")
    if sub_bom["qty_per_subcomponent"].isna().any():
        _fail("subcomponents_bom.csv has invalid qty_per_subcomponent values.")

    merged = forecast.merge(bom, on="item", how="left")

    if merged["component"].isna().any():
        missing_items = sorted(set(merged.loc[merged["component"].isna(), "item"].tolist()))
        _fail(f"These forecast items are missing from recipes_bom.csv: {missing_items}")

    merged["required_qty"] = merged["forecast_qty"] * merged["quantity per unit"]

    direct = merged[merged["component_type"].isin(["ingredient", "packaging"])].copy()
    subcomp = merged[merged["component_type"] == "subcomponent"].copy()

    if not subcomp.empty:
        expanded = subcomp.merge(
            sub_bom,
            left_on="component",
            right_on="subcomponent",
            how="left"
        )

        if expanded["ingredient"].isna().any():
            missing_subs = sorted(set(expanded.loc[expanded["ingredient"].isna(), "component"].tolist()))
            _fail(f"These subcomponents are missing from subcomponents_bom.csv: {missing_subs}")

        expanded["required_qty"] = expanded["required_qty"] * expanded["qty_per_subcomponent"]

        expanded_out = expanded[[
            "week_end_date",
            "ingredient",
            "required_qty"
        ]].rename(columns={"ingredient": "component"})

        expanded_out["uom"] = "kg"
        expanded_out["component_type"] = "ingredient"
    else:
        expanded_out = pd.DataFrame(columns=["week_end_date", "component", "required_qty", "uom", "component_type"])

    direct_out = direct[[
        "week_end_date",
        "component",
        "required_qty",
        "kg",
        "component_type"
    ]].rename(columns={"kg": "uom"})

    combined = pd.concat([direct_out, expanded_out], ignore_index=True)

    requirements = (
        combined.groupby(["week_end_date", "component", "uom", "component_type"], as_index=False)["required_qty"]
        .sum()
        .sort_values(["week_end_date", "component_type", "component"])
        .reset_index(drop=True)
    )

    requirements["required_qty"] = requirements["required_qty"].apply(round_up_qty)

    return requirements


def compute_recommended_purchases(
    requirements: pd.DataFrame,
    inventory: pd.DataFrame
) -> pd.DataFrame:
    inventory = inventory.copy()

    inventory["component"] = _normalize_str(inventory["component"])
    inventory["unit_of_measurement"] = _normalize_str(inventory["unit_of_measurement"]).str.lower()
    inventory["component_type"] = _normalize_str(inventory["component_type"]).str.lower()
    inventory["on_hand_qty"] = pd.to_numeric(inventory["on_hand_qty"], errors="coerce").fillna(0)

    merged = requirements.merge(
        inventory[["component", "unit_of_measurement", "component_type", "on_hand_qty"]],
        left_on=["component", "uom", "component_type"],
        right_on=["component", "unit_of_measurement", "component_type"],
        how="left"
    )

    merged["on_hand_qty"] = merged["on_hand_qty"].fillna(0)

    def safety_stock_row(row) -> int:
        if row["component_type"] == "ingredient":
            return round_up_qty(float(row["required_qty"]) * SAFETY_STOCK_PCT_INGREDIENTS)
        if row["component_type"] == "packaging":
            return round_up_qty(float(row["required_qty"]) * SAFETY_STOCK_PCT_PACKAGING)
        return 0

    merged["required_qty"] = merged["required_qty"].apply(round_up_qty)
    merged["on_hand_qty"] = merged["on_hand_qty"].apply(round_up_qty)
    merged["safety_stock"] = merged.apply(safety_stock_row, axis=1)

    merged["recommended_purchase_qty"] = (
        merged["required_qty"] + merged["safety_stock"] - merged["on_hand_qty"]
    ).clip(lower=0).apply(round_up_qty)

    out = merged[[
        "week_end_date",
        "component",
        "component_type",
        "uom",
        "required_qty",
        "safety_stock",
        "on_hand_qty",
        "recommended_purchase_qty"
    ]].sort_values(["week_end_date", "component_type", "component"]).reset_index(drop=True)

    return out


def save_outputs(requirements: pd.DataFrame, recommended: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    requirements.to_csv(OUT_REQUIREMENTS, index=False)
    recommended.to_csv(OUT_RECOMMENDED, index=False)

    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = EXPORTS_DIR / f"run_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    requirements.to_csv(run_dir / "requirements_components.csv", index=False)
    recommended.to_csv(run_dir / "recommended_purchases.csv", index=False)

    print("\nRequirements and recommended purchases generated successfully.")
    print(f"Requirements saved to: {OUT_REQUIREMENTS}")
    print(f"Recommended purchases saved to: {OUT_RECOMMENDED}")
    print(f"Snapshot saved to: {run_dir}\n")


def main() -> None:
    forecast, bom, sub_bom, inventory = load_inputs()
    validate_inputs(forecast, bom, sub_bom, inventory)

    forecast = choose_planning_weeks(forecast)
    requirements = compute_requirements_components(forecast, bom, sub_bom)
    recommended = compute_recommended_purchases(requirements, inventory)

    save_outputs(requirements, recommended)


if __name__ == "__main__":
    main()