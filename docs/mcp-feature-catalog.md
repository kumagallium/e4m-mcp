# E4M MCP サーバー 機能カタログ

E4M.jp の 14 ツール・32 API エンドポイントを MCP サーバーとして再実装するための設計カタログ。

## MCP サーバー構成方針

| 方針 | 内容 |
|------|------|
| 言語 | Python (`mcp` SDK) — 元の Django コードと同じ言語で移植しやすい |
| 単位 | 1 ツール群 = 1 MCP サーバー (独立してインストール可能) |
| ツール名 | `e4m_<機能名>` で統一 |
| バリデーション | Pydantic v2 |
| API キー管理 | 環境変数 (`MP_API_KEY` 等) |

---

## MCP サーバー一覧

### 1. `e4m-composition` — 組成変換

**ディレクトリ:** `mcp-servers/e4m-composition/`
**優先度:** ★★★ (最もよく使われる機能)

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_at2wt` | 原子% → 重量% | `composition: str` (例: "Al0.5Cu0.5") | 元素ごとの重量% |
| `e4m_wt2at` | 重量% → 原子% | `elements: list[{composition, wt}]` | 元素ごとの原子% |
| `e4m_vol2at` | 体積% → 原子% | `elements: list[{composition, vol}]`, `densities: list[float]` | 元素ごとの原子% |

**依存:** `pymatgen`

---

### 2. `e4m-calculator` — 体積・質量計算

**ディレクトリ:** `mcp-servers/e4m-calculator/`
**優先度:** ★★☆

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_volume_rectangular` | 直方体体積 | `x, y, height: float`, `unit: str` | 体積 (SI) |
| `e4m_volume_cylinder` | 円柱体積 | `radius, height: float`, `unit: str` | 体積 (SI) |
| `e4m_estimate_mass` | 質量推定 | `volume: float`, `unit: str`, `density: float` | 質量 (g) |
| `e4m_get_weigh` | 組成の元素重量 | `mass: float`, `unit: str`, `composition: str` | 元素ごとの質量 |

**依存:** `pint`, `pymatgen`

---

### 3. `e4m-materials-project` — Materials Project 連携

**ディレクトリ:** `mcp-servers/e4m-materials-project/`
**優先度:** ★★★

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_get_mp_data` | 組成から物性データ取得 | `composition: str` | material_id, 結晶系, band_gap, エネルギー等 |
| `e4m_get_density` | 密度取得 | `composition: str` または `mpid: str` | 密度 (g/cm³), mpid |
| `e4m_get_delaunay` | 3D デロネー可視化データ | `mpid: str`, `scale: int`, `is_niggli: bool` | Plotly JSON |

**依存:** `mp-api`, `pymatgen`, `scipy`, `plotly`
**環境変数:** `MP_API_KEY`

---

### 4. `e4m-starrydata` — Starrydata 熱電材料データベース

**ディレクトリ:** `mcp-servers/e4m-starrydata/`
**優先度:** ★★☆

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_search_starrydata` | 熱電材料の実験データ検索 | `include_elements: str`, `exclude_elements: str`, `base_composition: str`, `properties: list[str]` | 物性データ表 (CSV/JSON) |
| `e4m_list_starrydata_props` | 利用可能なプロパティ一覧 | なし | プロパティ名リスト |

**利用可能プロパティ:** Temperature, Seebeck coefficient, Electrical conductivity, Thermal conductivity, ZT
**依存:** `pymatgen`, `pandas`
**データソース:** [Starrydata2](https://github.com/starrydata/starrydata_datasets) (自動ダウンロード)

---

### 5. `e4m-periodic-table` — 周期表・元素物性

**ディレクトリ:** `mcp-servers/e4m-periodic-table/`
**優先度:** ★★☆

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_get_element_properties` | 元素物性値の取得 | `elements: list[str]`, `properties: list[str]` | 元素ごとの物性値 |
| `e4m_list_properties` | 利用可能プロパティ一覧 | `source: "xenonpy"\|"pymatgen"` | プロパティ名リスト |
| `e4m_get_periodic_table` | 全周期表データ | `properties: list[str]` | 全元素の物性値 |

**データソース:** df_pt.csv (独自), df_pt_pymatgen.csv (Pymatgen)
**依存:** `pymatgen`, `pandas`

---

### 6. `e4m-units` — 単位変換

**ディレクトリ:** `mcp-servers/e4m-units/`
**優先度:** ★☆☆

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_convert_unit` | 単位変換 | `value: float`, `from_unit: str`, `to_unit: str` | 変換後の値と単位 |
| `e4m_list_units` | 利用可能な単位一覧 | なし | SI単位・接頭辞一覧 |

**依存:** `pint`

---

### 7. `e4m-references` — 文献・DOI フォーマット

**ディレクトリ:** `mcp-servers/e4m-references/`
**優先度:** ★☆☆ (Java サブプロセス依存あり、要検討)

| MCP ツール | 説明 | 入力 | 出力 |
|-----------|------|------|------|
| `e4m_ref2doi` | 文献テキスト → DOI | `reference: str` | DOI |
| `e4m_doi2format` | DOI → 参考文献フォーマット | `doi: str`, `style: str` | フォーマット済み参考文献 |
| `e4m_ref2format` | 文献テキスト → フォーマット済み | `reference: str`, `style: str` | フォーマット済み参考文献 |
| `e4m_list_styles` | 利用可能スタイル一覧 | なし | スタイル名リスト |

**依存:** Java (search_based_reference_matcher), Crosscite API
**注意:** Java 依存を Python 実装に置き換えることを検討

---

## 実装優先順位

```
Phase 1 (すぐに価値が出る):
  ① e4m-composition   ← 計算が多いユーザーに即効
  ② e4m-materials-project ← 材料検索の核心
  ③ e4m-starrydata    ← 熱電材料研究者向け

Phase 2:
  ④ e4m-periodic-table
  ⑤ e4m-calculator

Phase 3:
  ⑥ e4m-units
  ⑦ e4m-references (Java 依存を要リファクタ)
```

---

## 各 MCP サーバーのディレクトリ構成

```
mcp-servers/<サーバー名>/
├── README.md          # ツール仕様・使い方
├── pyproject.toml     # 依存関係
├── .env.example       # 必要な環境変数
└── src/
    └── <サーバー名>/
        ├── __init__.py
        ├── server.py  # MCP サーバーエントリポイント
        └── tools/
            └── *.py   # ツール実装
```

---

## Claude Code への組み込み方法 (.claude/settings.json)

```json
{
  "mcpServers": {
    "e4m-composition": {
      "command": "python",
      "args": ["-m", "e4m_composition"],
      "cwd": "/path/to/mcp-servers/e4m-composition"
    },
    "e4m-materials-project": {
      "command": "python",
      "args": ["-m", "e4m_materials_project"],
      "env": {
        "MP_API_KEY": "${MP_API_KEY}"
      },
      "cwd": "/path/to/mcp-servers/e4m-materials-project"
    }
  }
}
```
