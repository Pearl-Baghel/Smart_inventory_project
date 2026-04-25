from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIENT_XLSX = PROJECT_ROOT / "data" / "client_inputs" / "namaste_inputs.xlsx"
SALES_CSV = PROJECT_ROOT / "data" / "processed" / "sales.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"

REQUIRED_SHEETS = [
    "recipes_bom",
    "subcomponents_bom",
    "inventory_snapshot",
    "purchases_log",
    "waste_log",
]

REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "sales": ["date", "item", "quantity sold", "price", "market location"],
    "recipes_bom": ["item", "component", "quantity per unit", "kg", "component_type"],
    "subcomponents_bom": [
        "subcomponent",
        "ingredient",
        "qty_per_subcomponent",
        "sub_unit_of_measurement",
        "ingredient_unit_of_measuresurment",
    ],
    "inventory_snapshot": ["snapshot_date", "component", "on_hand_qty", "unit_of_measurement", "component_type"],
    "purchases_log": ["purchase_date", "component", "qty_purchased", "unit_of_measurement", "unit_cost"],
        "waste_log": ["week_end_date", "item", "waste_qty_units", "reason", "estimated_cost", "Stock out flag", "Lost Sales Estimate",
    ],
}

ALLOWED_UOM = {"kg", "each"}
ALLOWED_COMPONENT_TYPES_BOM = {"ingredient", "packaging", "subcomponent"}
ALLOWED_COMPONENT_TYPES_INV = {"ingredient", "packaging"}


@dataclass
class ValidationIssue:
    sheet: str
    message: str


def _fail(issues: List[ValidationIssue]) -> None:
    print("\nValidation failed:\n")
    for i, issue in enumerate(issues, start=1):
        print(f"{i}. [{issue.sheet}] {issue.message}")
    raise SystemExit(1)


def _normalize_str_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def _ensure_columns(df: pd.DataFrame, required: List[str], sheet: str, issues: List[ValidationIssue]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(sheet, f"Missing columns: {missing}. Found: {list(df.columns)}"))


def _parse_date(df: pd.DataFrame, col: str, sheet: str, issues: List[ValidationIssue]) -> None:
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    if df[col].isna().any():
        bad_rows = df[df[col].isna()].index.tolist()[:10]
        issues.append(ValidationIssue(sheet, f"Invalid dates in '{col}'. Example rows: {bad_rows}"))


def _parse_numeric(df: pd.DataFrame, col: str, sheet: str, issues: List[ValidationIssue], allow_zero: bool = True) -> None:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[col].isna().any():
        bad_rows = df[df[col].isna()].index.tolist()[:10]
        issues.append(ValidationIssue(sheet, f"'{col}' must be numeric. Example rows: {bad_rows}"))
        return
    if not allow_zero and (df[col] <= 0).any():
        bad_rows = df[df[col] <= 0].index.tolist()[:10]
        issues.append(ValidationIssue(sheet, f"'{col}' must be > 0. Example rows: {bad_rows}"))


def _validate_uom(df: pd.DataFrame, uom_col: str, sheet: str, issues: List[ValidationIssue]) -> None:
    df[uom_col] = _normalize_str_series(df[uom_col]).str.lower()
    bad = sorted(set(df.loc[~df[uom_col].isin(ALLOWED_UOM), uom_col].tolist()))
    if bad:
        issues.append(ValidationIssue(sheet, f"Invalid units in '{uom_col}': {bad}. Allowed: {sorted(ALLOWED_UOM)}"))


def _validate_component_type_bom(df: pd.DataFrame, sheet: str, issues: List[ValidationIssue]) -> None:
    df["component_type"] = _normalize_str_series(df["component_type"]).str.lower()
    bad = sorted(set(df.loc[~df["component_type"].isin(ALLOWED_COMPONENT_TYPES_BOM), "component_type"].tolist()))
    if bad:
        issues.append(ValidationIssue(sheet, f"Invalid component_type values: {bad}"))


def _validate_component_type_inv(df: pd.DataFrame, sheet: str, issues: List[ValidationIssue]) -> None:
    df["component_type"] = _normalize_str_series(df["component_type"]).str.lower()
    bad = sorted(set(df.loc[~df["component_type"].isin(ALLOWED_COMPONENT_TYPES_INV), "component_type"].tolist()))
    if bad:
        issues.append(ValidationIssue(sheet, f"Invalid component_type values: {bad}"))


def read_excel_sheets(xlsx_path: Path, issues: List[ValidationIssue]) -> Dict[str, pd.DataFrame]:
    if not xlsx_path.exists():
        issues.append(ValidationIssue("system", f"Excel file not found: {xlsx_path}"))
        _fail(issues)

    xl = pd.ExcelFile(xlsx_path)
    available = set(xl.sheet_names)
    missing_sheets = [s for s in REQUIRED_SHEETS if s not in available]
    if missing_sheets:
        issues.append(ValidationIssue("system", f"Missing tabs: {missing_sheets}. Found: {sorted(available)}"))
        _fail(issues)

    dfs: Dict[str, pd.DataFrame] = {}
    for sheet in REQUIRED_SHEETS:
        df = pd.read_excel(xlsx_path, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        dfs[sheet] = df

    return dfs


def read_sales_csv(path: Path, issues: List[ValidationIssue]) -> pd.DataFrame:
    if not path.exists():
        issues.append(ValidationIssue("sales", f"Sales file not found: {path}. Run raw_to_sales_clean.py first."))
        _fail(issues)

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    _ensure_columns(df, REQUIRED_COLUMNS["sales"], "sales", issues)
    if issues:
        _fail(issues)
    return df


def _validate_consistency(
    sales: pd.DataFrame,
    bom: pd.DataFrame,
    sub_bom: pd.DataFrame,
    inventory: pd.DataFrame,
    issues: List[ValidationIssue],
) -> None:
    sales_items = set(_normalize_str_series(sales["item"]))
    bom_items = set(_normalize_str_series(bom["item"]))
    missing_items = sorted(list(sales_items - bom_items))
    if missing_items:
        issues.append(ValidationIssue("cross_check", f"Items in sales missing from recipes_bom: {missing_items}"))

    used_subcomponents = set(_normalize_str_series(bom.loc[bom["component_type"] == "subcomponent", "component"]))
    defined_subcomponents = set(_normalize_str_series(sub_bom["subcomponent"]))
    missing_sub = sorted(list(used_subcomponents - defined_subcomponents))
    if missing_sub:
        issues.append(ValidationIssue("cross_check", f"Subcomponents missing from subcomponents_bom: {missing_sub}"))

    bom_components = set(_normalize_str_series(bom["component"]))
    sub_ingredients = set(_normalize_str_series(sub_bom["ingredient"]))
    valid_inventory_components = bom_components.union(sub_ingredients)

    inv_components = set(_normalize_str_series(inventory["component"]))
    unknown_inv = sorted(list(inv_components - valid_inventory_components))
    if unknown_inv:
        issues.append(ValidationIssue("cross_check", f"Inventory components not found in BOM/subcomponents: {unknown_inv}"))

    bad_packaging_uom = bom[(bom["component_type"] == "packaging") & (bom["kg"] != "each")]
    if not bad_packaging_uom.empty:
        issues.append(ValidationIssue("recipes_bom", "Packaging rows must use 'each' in column 'kg'."))

    bad_ing_uom = bom[(bom["component_type"].isin(["ingredient", "subcomponent"])) & (bom["kg"] != "kg")]
    if not bad_ing_uom.empty:
        issues.append(ValidationIssue("recipes_bom", "Ingredient/subcomponent rows must use 'kg' in column 'kg'."))


def main() -> None:
    issues: List[ValidationIssue] = []

    sales = read_sales_csv(SALES_CSV, issues)
    dfs = read_excel_sheets(CLIENT_XLSX, issues)

    for sheet, df in dfs.items():
        _ensure_columns(df, REQUIRED_COLUMNS[sheet], sheet, issues)

    if issues:
        _fail(issues)

    sales["item"] = _normalize_str_series(sales["item"])
    sales["market location"] = _normalize_str_series(sales["market location"])
    _parse_date(sales, "date", "sales", issues)
    _parse_numeric(sales, "quantity sold", "sales", issues, allow_zero=False)
    _parse_numeric(sales, "price", "sales", issues, allow_zero=False)

    bom = dfs["recipes_bom"].copy()
    bom["item"] = _normalize_str_series(bom["item"])
    bom["component"] = _normalize_str_series(bom["component"])
    bom["kg"] = _normalize_str_series(bom["kg"]).str.lower()
    _validate_uom(bom, "kg", "recipes_bom", issues)
    _validate_component_type_bom(bom, "recipes_bom", issues)
    _parse_numeric(bom, "quantity per unit", "recipes_bom", issues, allow_zero=False)

    sub_bom = dfs["subcomponents_bom"].copy()
    sub_bom["subcomponent"] = _normalize_str_series(sub_bom["subcomponent"])
    sub_bom["ingredient"] = _normalize_str_series(sub_bom["ingredient"])
    sub_bom["sub_unit_of_measurement"] = _normalize_str_series(sub_bom["sub_unit_of_measurement"]).str.lower()
    sub_bom["ingredient_unit_of_measuresurment"] = _normalize_str_series(
        sub_bom["ingredient_unit_of_measuresurment"]
    ).str.lower()
    _parse_numeric(sub_bom, "qty_per_subcomponent", "subcomponents_bom", issues, allow_zero=False)

    bad_sub_uom = sorted(set(sub_bom.loc[sub_bom["sub_unit_of_measurement"] != "kg", "sub_unit_of_measurement"].tolist()))
    bad_ing_uom = sorted(set(sub_bom.loc[sub_bom["ingredient_unit_of_measuresurment"] != "kg", "ingredient_unit_of_measuresurment"].tolist()))
    if bad_sub_uom:
        issues.append(ValidationIssue("subcomponents_bom", f"sub_unit_of_measurement should be 'kg'. Found: {bad_sub_uom}"))
    if bad_ing_uom:
        issues.append(ValidationIssue("subcomponents_bom", f"ingredient_unit_of_measuresurment should be 'kg'. Found: {bad_ing_uom}"))

    inventory = dfs["inventory_snapshot"].copy()
    inventory["component"] = _normalize_str_series(inventory["component"])
    inventory["unit_of_measurement"] = _normalize_str_series(inventory["unit_of_measurement"]).str.lower()
    _parse_date(inventory, "snapshot_date", "inventory_snapshot", issues)
    _validate_uom(inventory, "unit_of_measurement", "inventory_snapshot", issues)
    _validate_component_type_inv(inventory, "inventory_snapshot", issues)
    _parse_numeric(inventory, "on_hand_qty", "inventory_snapshot", issues, allow_zero=True)

    purchases = dfs["purchases_log"].copy()
    purchases["component"] = _normalize_str_series(purchases["component"])
    purchases["unit_of_measurement"] = _normalize_str_series(purchases["unit_of_measurement"]).str.lower()
    _parse_date(purchases, "purchase_date", "purchases_log", issues)
    _validate_uom(purchases, "unit_of_measurement", "purchases_log", issues)
    _parse_numeric(purchases, "qty_purchased", "purchases_log", issues, allow_zero=False)
    _parse_numeric(purchases, "unit_cost", "purchases_log", issues, allow_zero=False)

    waste = dfs["waste_log"].copy()
    waste["item"] = _normalize_str_series(waste["item"])
    waste["reason"] = _normalize_str_series(waste["reason"])
    _parse_date(waste, "week_end_date", "waste_log", issues)
    _parse_numeric(waste, "waste_qty_units", "waste_log", issues, allow_zero=True)
    _parse_numeric(waste, "estimated_cost", "waste_log", issues, allow_zero=True)
    _parse_numeric(waste, "Stock out flag", "waste_log", issues, allow_zero=True)
    _parse_numeric(waste, "Lost Sales Estimate", "waste_log", issues, allow_zero=True)

    _validate_consistency(sales, bom, sub_bom, inventory, issues)

    if issues:
        _fail(issues)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    outputs: List[Tuple[str, pd.DataFrame]] = [
        ("sales.csv", sales),
        ("recipes_bom.csv", bom),
        ("subcomponents_bom.csv", sub_bom),
        ("inventory_snapshot.csv", inventory),
        ("purchases_log.csv", purchases),
        ("waste_log.csv", waste),
    ]

    for filename, df in outputs:
        df.to_csv(PROCESSED_DIR / filename, index=False)

    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = EXPORTS_DIR / f"run_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for filename, df in outputs:
        df.to_csv(run_dir / filename, index=False)

    print("\nValidation successful.")
    print(f"Processed files saved to: {PROCESSED_DIR}")
    print(f"Run snapshot saved to: {run_dir}\n")


if __name__ == "__main__":
    main()