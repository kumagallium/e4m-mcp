"""E4M ユーティリティ MCP サーバー（単位変換 / DOI 文献フォーマット）"""
from __future__ import annotations
import os
from typing import Annotated
import pint
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import Field

u = pint.UnitRegistry()
u.define('fraction = [] = frac')
u.define('percent = 1e-2 frac = pct')
u.define('ppm = 1e-6 fraction')

CROSSCITE_URL = "https://citation.crosscite.org/format"
COMMON_STYLES = [
    "apa", "vancouver", "harvard-cite-them-right",
    "nature", "science", "cell",
    "ieee", "chicago-author-date",
    "american-chemical-society", "royal-society-of-chemistry",
    "american-physics-society",
    "journal-of-applied-physics",
    "acta-materialia",
    "journal-of-materials-science",
]

mcp = FastMCP(
    name="e4m-utils",
    instructions="汎用ユーティリティツール群。物理単位変換と DOI 文献フォーマット変換を提供する。",
)

# ── 単位変換 ──

@mcp.tool()
def e4m_convert_unit(
    value: Annotated[str, Field(description="変換する値と単位 (例: '1.0 meter', '100 celsius')")],
    to_unit: Annotated[str, Field(description="変換先の単位 (例: 'kilometer', 'fahrenheit')")],
) -> dict:
    """物理量の単位を変換する。Pint でサポートされる全単位に対応。"""
    try:
        result = u.Quantity(value).to(to_unit)
        return {"value": result.magnitude, "units": str(result.units)}
    except Exception as e:
        raise ValueError(f"単位変換に失敗しました: {e}") from e

@mcp.tool()
def e4m_list_units() -> dict:
    """利用可能な SI 接頭辞と単位カテゴリの一覧を返す。"""
    prefixes = [
        {"name": "yocto","symbol":"y","value":1e-24}, {"name":"zepto","symbol":"z","value":1e-21},
        {"name":"atto","symbol":"a","value":1e-18},   {"name":"femto","symbol":"f","value":1e-15},
        {"name":"pico","symbol":"p","value":1e-12},   {"name":"nano","symbol":"n","value":1e-9},
        {"name":"micro","symbol":"u","value":1e-6},   {"name":"milli","symbol":"m","value":1e-3},
        {"name":"centi","symbol":"c","value":1e-2},   {"name":"deci","symbol":"d","value":1e-1},
        {"name":"deca","symbol":"da","value":1e+1},   {"name":"hecto","symbol":"h","value":1e2},
        {"name":"kilo","symbol":"k","value":1e3},     {"name":"mega","symbol":"M","value":1e6},
        {"name":"giga","symbol":"G","value":1e9},     {"name":"tera","symbol":"T","value":1e12},
    ]
    examples = [
        {"category":"長さ","examples":["meter","kilometer","millimeter","inch","foot","angstrom"]},
        {"category":"質量","examples":["gram","kilogram","milligram","pound","ounce"]},
        {"category":"時間","examples":["second","minute","hour","day"]},
        {"category":"温度","examples":["celsius","fahrenheit","kelvin"]},
        {"category":"圧力","examples":["pascal","bar","atm","torr","psi"]},
        {"category":"エネルギー","examples":["joule","calorie","eV","kWh"]},
        {"category":"体積","examples":["liter","milliliter","cm^3","m^3"]},
        {"category":"密度","examples":["g/cm^3","kg/m^3"]},
    ]
    return {"prefixes": prefixes, "unit_categories": examples}

# ── 文献フォーマット ──

@mcp.tool()
def e4m_doi2format(
    doi: Annotated[str, Field(description="DOI (例: '10.1038/nature12373')")],
    style: Annotated[str, Field(description="引用スタイル (例: 'apa', 'nature', 'ieee')")] = "apa",
    lang: Annotated[str, Field(description="言語コード (例: 'en-US', 'ja-JP')")] = "en-US",
) -> str:
    """DOI を指定した引用スタイルでフォーマットされた参考文献に変換する。"""
    doi_clean = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    url = f"{CROSSCITE_URL}?doi={doi_clean}&style={style}&lang={lang}"
    try:
        r = requests.get(url, headers={"Accept": "text/x-bibliography"}, timeout=15)
        r.encoding = "UTF-8"
        text = r.text.strip()
        if text == "metadata for DOI not found":
            raise ValueError(f"DOI '{doi_clean}' のメタデータが見つかりませんでした。")
        return text
    except requests.RequestException as e:
        raise ValueError(f"Crosscite API へのアクセスに失敗しました: {e}") from e

@mcp.tool()
def e4m_list_citation_styles() -> list[str]:
    """利用可能な引用スタイルの一覧を返す。"""
    return COMMON_STYLES

# ── エントリポイント ──

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="E4M ユーティリティ MCP サーバー")
    parser.add_argument("--transport", choices=["stdio", "sse"], default=os.environ.get("TRANSPORT", "stdio"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8003)
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
