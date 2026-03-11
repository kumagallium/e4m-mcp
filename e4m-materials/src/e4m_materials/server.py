"""E4M 材料計算 MCP サーバー（組成変換 / 体積・質量計算 / 元素物性）"""
from __future__ import annotations
import math
import os
import pathlib
from typing import Annotated, Literal
import pandas as pd
import pint
import pymatgen.core as mg
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

u = pint.UnitRegistry()
u.define('fraction = [] = frac')
u.define('percent = 1e-2 frac = pct')
u.define('ppm = 1e-6 fraction')

DATA_DIR = pathlib.Path(__file__).parent.parent.parent / "data"

mcp = FastMCP(
    name="e4m-materials",
    instructions=(
        "材料科学ツール群。"
        "組成変換（原子%・重量%・体積%）、体積・質量計算、元素物性データを提供する。"
    ),
)

# ── 入力スキーマ ──

class WtComponent(BaseModel):
    composition: str = Field(description="組成式 (例: Al, Fe2O3)")
    wt: float = Field(gt=0, description="重量%")

class VolComponent(BaseModel):
    composition: str = Field(description="組成式 (例: Al, Fe2O3)")
    vol: float = Field(gt=0, description="体積%")
    density: float = Field(gt=0, description="密度 (g/cm³)")

# ── 組成変換 ──

@mcp.tool()
def e4m_at2wt(
    composition: Annotated[str, Field(description="組成式 (例: 'Al0.5Cu0.5', 'Fe3O4')")],
) -> list[dict]:
    """原子% → 重量% に変換する。"""
    try:
        comp_dict = dict(mg.Composition(composition).fractional_composition.as_dict())
        weighted, total = [], 0.0
        for el, ratio in comp_dict.items():
            am = float(mg.Element(el).atomic_mass)
            w = am * ratio
            weighted.append({"element": el, "atomic_mass": am, "weight": w})
            total += w
        return [{"element": i["element"], "atomic_mass": i["atomic_mass"], "value": i["weight"] / total} for i in weighted]
    except Exception as e:
        raise ValueError(f"組成式の解析に失敗しました: {composition!r} — {e}") from e

@mcp.tool()
def e4m_wt2at(
    elements: Annotated[list[WtComponent], Field(description="重量% で指定した元素・化合物のリスト")],
) -> list[dict]:
    """重量% → 原子% に変換する。"""
    try:
        tmp, total_mol = [], 0.0
        for item in elements:
            mw = float(mg.Composition(item.composition).weight)
            mol = item.wt / mw
            tmp.append({"composition": item.composition, "mol": mol, "weight": mw})
            total_mol += mol
        return [{"composition": t["composition"], "value": t["mol"] / total_mol, "weight": t["weight"]} for t in tmp]
    except Exception as e:
        raise ValueError(f"変換に失敗しました: {e}") from e

@mcp.tool()
def e4m_vol2at(
    elements: Annotated[list[VolComponent], Field(description="体積% と密度を指定した元素・化合物のリスト")],
) -> list[dict]:
    """体積% → 原子% に変換する。"""
    try:
        tmp, total_at = [], 0.0
        for item in elements:
            mw = float(mg.Composition(item.composition).weight)
            at = item.vol * (item.density / mw)
            tmp.append({"composition": item.composition, "at": at, "density": item.density, "weight": mw})
            total_at += at
        return [{"composition": t["composition"], "value": t["at"] / total_at, "density": t["density"], "weight": t["weight"]} for t in tmp]
    except Exception as e:
        raise ValueError(f"変換に失敗しました: {e}") from e

# ── 体積・質量計算 ──

@mcp.tool()
def e4m_volume_rectangular(
    x: Annotated[float, Field(gt=0, description="x 方向の長さ")],
    y: Annotated[float, Field(gt=0, description="y 方向の長さ")],
    height: Annotated[float, Field(gt=0, description="高さ")],
    unit: Annotated[str, Field(description="長さの単位 (例: 'mm', 'cm', 'inch')")],
) -> dict:
    """直方体の体積を計算する。"""
    try:
        vol = u.Quantity(x, unit) * u.Quantity(y, unit) * u.Quantity(height, unit)
        return {"value": vol.magnitude, "units": str(vol.units)}
    except Exception as e:
        raise ValueError(f"計算に失敗しました: {e}") from e

@mcp.tool()
def e4m_volume_cylinder(
    radius: Annotated[float, Field(gt=0, description="半径")],
    height: Annotated[float, Field(gt=0, description="高さ")],
    unit: Annotated[str, Field(description="長さの単位 (例: 'mm', 'cm', 'inch')")],
) -> dict:
    """円柱の体積を計算する。"""
    try:
        r = u.Quantity(radius, unit)
        h = u.Quantity(height, unit)
        vol = (r ** 2) * math.pi * h
        return {"value": vol.magnitude, "units": str(vol.units)}
    except Exception as e:
        raise ValueError(f"計算に失敗しました: {e}") from e

@mcp.tool()
def e4m_estimate_mass(
    volume: Annotated[float, Field(gt=0, description="体積の値")],
    volume_unit: Annotated[str, Field(description="体積の単位 (例: 'cm^3', 'mm^3')")],
    density: Annotated[float, Field(gt=0, description="密度 (g/cm³)")],
) -> dict:
    """体積と密度から質量を推定する。"""
    try:
        si_v = u.Quantity(volume, volume_unit)
        si_d = u.Quantity(density, "g/cm^3").to(u.g / u.parse_expression(volume_unit))
        mass = si_v * si_d
        return {"value": mass.magnitude, "units": str(mass.units)}
    except Exception as e:
        raise ValueError(f"計算に失敗しました: {e}") from e

@mcp.tool()
def e4m_get_atom_percent(
    composition: Annotated[str, Field(description="組成式 (例: 'Al3V', 'Fe3O4')")],
) -> dict:
    """組成式から各元素の原子分率を返す。"""
    try:
        return dict(mg.Composition(composition).fractional_composition.as_dict())
    except Exception as e:
        raise ValueError(f"組成解析に失敗しました: {e}") from e

@mcp.tool()
def e4m_get_weigh(
    mass: Annotated[float, Field(gt=0, description="全体の質量")],
    mass_unit: Annotated[str, Field(description="質量の単位 (例: 'gram', 'kilogram', 'mg')")],
    composition: Annotated[str, Field(description="組成式 (例: 'Al3V', 'Fe2O3')")],
) -> list[dict]:
    """指定した質量を組成比に応じて各元素に分配する。"""
    try:
        si_w = u.Quantity(mass, mass_unit)
        atom_dict = dict(mg.Composition(composition).fractional_composition.as_dict())
        all_mol = sum(float(mg.Element(el).atomic_mass) * v for el, v in atom_dict.items())
        return [
            {"element": el, "atomic_mass": float(mg.Element(el).atomic_mass),
             "value": si_w.magnitude * (float(mg.Element(el).atomic_mass) * v) / all_mol, "unit": str(si_w.units)}
            for el, v in atom_dict.items()
        ]
    except Exception as e:
        raise ValueError(f"計算に失敗しました: {e}") from e

# ── 元素物性 ──

def _load_df(source: str) -> pd.DataFrame:
    path = DATA_DIR / ("df_pt_pymatgen.csv" if source == "pymatgen" else "df_pt.csv")
    if not path.exists():
        raise FileNotFoundError(f"データファイルが見つかりません: {path}")
    return pd.read_csv(path, index_col=0)

@mcp.tool()
def e4m_list_element_properties(
    source: Annotated[Literal["xenonpy", "pymatgen"], Field(description="データソース")] = "pymatgen",
) -> list[str]:
    """利用可能な元素物性プロパティの一覧を返す。"""
    df = _load_df(source)
    return [c for c in df.columns if c not in ("symbol", "name", "atomic_number")]

@mcp.tool()
def e4m_get_element_properties(
    elements: Annotated[list[str], Field(description="元素記号のリスト (例: ['Fe', 'Cu', 'Al'])")],
    properties: Annotated[list[str], Field(description="取得するプロパティ名のリスト")] = None,
    source: Annotated[Literal["xenonpy", "pymatgen"], Field(description="データソース")] = "pymatgen",
) -> list[dict]:
    """指定した元素の物性値を返す。"""
    df = _load_df(source)
    sym_col = "symbol" if "symbol" in df.columns else df.columns[0]
    result = df[df[sym_col].isin(elements)]
    if properties:
        cols = [c for c in [sym_col, "name"] + properties if c in df.columns]
        result = result[cols]
    return result.fillna("").to_dict(orient="records")

@mcp.tool()
def e4m_get_periodic_table(
    properties: Annotated[list[str], Field(description="取得するプロパティ名のリスト。省略時は全カラム")] = None,
    source: Annotated[Literal["xenonpy", "pymatgen"], Field(description="データソース")] = "pymatgen",
) -> list[dict]:
    """全元素の物性データを返す。"""
    df = _load_df(source)
    if properties:
        sym_col = "symbol" if "symbol" in df.columns else df.columns[0]
        cols = [c for c in [sym_col, "name"] + properties if c in df.columns]
        df = df[cols]
    return df.fillna("").to_dict(orient="records")

# ── エントリポイント ──

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="E4M 材料計算 MCP サーバー")
    parser.add_argument("--transport", choices=["stdio", "sse"], default=os.environ.get("TRANSPORT", "stdio"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
