"""E4M 外部データ連携 MCP サーバー（Materials Project / Starrydata）"""
from __future__ import annotations
import io
import os
import pathlib
import zipfile
from typing import Annotated
import pandas as pd
import pymatgen.core as mg
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import Field

DATA_DIR = pathlib.Path(__file__).parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "allstarrydata.csv"
STARRYDATA_ZIP_URL = (
    "https://github.com/starrydata/starrydata_datasets/releases/latest/download/allstarrydata.zip"
)
REMOVE_COLS = {"projectname", "sampleinfo", "elements", "sampleid", "figureid"}
BASE_COLS = ["sid", "DOI", "published", "samplename", "composition", "base_composition_pred"]

_ENV_API_KEY = os.environ.get("MP_API_KEY", "")
_df_cache: pd.DataFrame | None = None

def _resolve_key(api_key: str) -> str:
    key = api_key.strip() or _ENV_API_KEY
    if not key:
        raise ValueError(
            "Materials Project の API キーが必要です。\n"
            "api_key 引数に指定するか、MP_API_KEY 環境変数を設定してください。\n"
            "キーの取得: https://materialsproject.org/api"
        )
    return key

def _load_starrydata() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache
    if DATA_FILE.exists():
        _df_cache = pd.read_csv(DATA_FILE, index_col=0)
        return _df_cache
    raise FileNotFoundError(
        "Starrydata データファイルが見つかりません。"
        "e4m_download_starrydata ツールを先に実行してください。"
    )

mcp = FastMCP(
    name="e4m-data",
    instructions=(
        "外部データベース連携ツール群。"
        "Materials Project（結晶構造・物性）と Starrydata（熱電材料）を検索できる。"
        "Materials Project の利用には api_key 引数または MP_API_KEY 環境変数が必要。"
    ),
)

# ── Materials Project ──

@mcp.tool()
def e4m_get_mp_data(
    composition: Annotated[str, Field(description="組成式 (例: 'PbTe', 'Fe2O3', 'Al')")],
    api_key: Annotated[str, Field(description="Materials Project API キー。未指定時は MP_API_KEY 環境変数を使用")] = "",
) -> dict:
    """組成式から Materials Project の物性データを取得する。energy_above_hull でソートして返す。"""
    key = _resolve_key(api_key)
    try:
        from mp_api.client import MPRester
        with MPRester(key) as mpr:
            results = mpr.summary.search(
                formula=composition,
                fields=["material_id", "formula_pretty", "symmetry",
                        "formation_energy_per_atom", "energy_above_hull", "band_gap"],
            )
        rows = []
        for r in results:
            d = r.dict()
            rows.append({
                "mpid": d["material_id"],
                "formula": d["formula_pretty"],
                "symmetry": d["symmetry"]["symbol"] if d.get("symmetry") else "",
                "formation_energy_per_atom": round(float(d.get("formation_energy_per_atom") or 0), 4),
                "energy_above_hull": round(float(d.get("energy_above_hull") or 0), 4),
                "band_gap": round(float(d.get("band_gap") or 0), 4),
            })
        rows.sort(key=lambda x: x["energy_above_hull"])
        return {"data": rows, "count": len(rows)}
    except Exception as e:
        raise ValueError(f"Materials Project API エラー: {e}") from e

@mcp.tool()
def e4m_get_density(
    composition: Annotated[str, Field(description="組成式 (例: 'Al', 'Fe2O3'). mpid 指定時は空でも可")] = "",
    mpid: Annotated[str, Field(description="Materials Project の material_id (例: 'mp-134')")] = "",
    api_key: Annotated[str, Field(description="Materials Project API キー。未指定時は MP_API_KEY 環境変数を使用")] = "",
) -> dict:
    """組成式または mpid から密度 (g/cm³) を取得する。energy_above_hull が最小の構造を使用。"""
    key = _resolve_key(api_key)
    if not composition and not mpid:
        raise ValueError("composition または mpid のどちらかを指定してください。")
    try:
        from mp_api.client import MPRester
        with MPRester(key) as mpr:
            if mpid:
                structure = mpr.get_structure_by_material_id(mpid)
                return {"value": float(structure.density), "units": "g/cm^3", "mpid": mpid}
            else:
                results = mpr.summary.search(formula=composition, fields=["material_id", "energy_above_hull", "density"])
                rows = [r.dict() for r in results]
                df = pd.DataFrame(rows).sort_values("energy_above_hull")
                return {"value": float(df["density"].iloc[0]), "units": "g/cm^3", "mpid": str(df["material_id"].iloc[0])}
    except Exception as e:
        raise ValueError(f"密度の取得に失敗しました: {e}") from e

# ── Starrydata ──

@mcp.tool()
def e4m_download_starrydata() -> str:
    """Starrydata の最新データセットを GitHub からダウンロードして保存する。初回利用時または更新時に実行してください。"""
    global _df_cache
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(STARRYDATA_ZIP_URL, timeout=120)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_names = [n for n in z.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError("ZIP 内に CSV ファイルが見つかりません。")
            with z.open(csv_names[0]) as f:
                df = pd.read_csv(f)
        df.to_csv(DATA_FILE)
        _df_cache = df
        return f"ダウンロード完了: {len(df)} 行のデータを保存しました。"
    except Exception as e:
        raise ValueError(f"ダウンロードに失敗しました: {e}") from e

@mcp.tool()
def e4m_list_starrydata_props() -> list[str]:
    """Starrydata で利用可能な物性プロパティ名の一覧を返す。"""
    df = _load_starrydata()
    return sorted(set(df.columns) - REMOVE_COLS - set(BASE_COLS))

@mcp.tool()
def e4m_search_starrydata(
    include_elements: Annotated[str, Field(description="含める元素 (カンマ区切り, 例: 'Pb,Te')")] = "",
    exclude_elements: Annotated[str, Field(description="除外する元素 (カンマ区切り, 例: 'Pb')")] = "",
    base_composition: Annotated[str, Field(description="基本組成式 (例: 'PbTe', 'CoSb3')")] = "",
    properties: Annotated[list[str], Field(description="取得するプロパティ (例: ['Temperature', 'Seebeck coefficient'])")] = None,
    max_rows: Annotated[int, Field(gt=0, le=1000, description="最大返却行数")] = 200,
) -> dict:
    """Starrydata 熱電材料データベースを検索する。"""
    df = _load_starrydata()
    df_res = df.copy()
    if include_elements:
        for el in include_elements.replace(" ", "").split(","):
            if el:
                df_res = df_res[df_res["elements"].str.contains(el + ",", na=False)]
    if exclude_elements:
        for el in exclude_elements.replace(" ", "").split(","):
            if el:
                df_res = df_res[~df_res["elements"].str.contains(el + ",", na=False)]
    if base_composition:
        reduced = mg.Composition(base_composition).reduced_formula
        df_res = df_res[df_res["base_composition_pred"] == reduced]
    select_props = properties or ["Temperature", "Seebeck coefficient"]
    cols = BASE_COLS + [p for p in select_props if p in df_res.columns]
    df_res = df_res[cols].fillna("").head(max_rows)
    records = df_res.to_dict(orient="records")
    all_props = sorted(set(df.columns) - REMOVE_COLS - set(BASE_COLS))
    return {"count": len(records), "headers": list(records[0].keys()) if records else [], "data": records, "available_properties": all_props}

# ── エントリポイント ──

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="E4M 外部データ連携 MCP サーバー")
    parser.add_argument("--transport", choices=["stdio", "sse"], default=os.environ.get("TRANSPORT", "stdio"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
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
