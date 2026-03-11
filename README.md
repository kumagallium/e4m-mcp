# e4m-mcp

材料科学に特化した [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) サーバー群。
[E4M.jp](https://e4m.jp) の便利ツールを AI Agent から呼び出せるように MCP サーバー化したものです。

Claude Code・Cursor・Dify などの MCP 対応 AI クライアントから利用できます。

---

## MCP サーバー一覧

| サーバー | 説明 | 主なツール |
|---------|------|-----------|
| [`e4m-utils`](e4m-utils/) | 汎用ユーティリティ | 単位変換・DOI 文献フォーマット |
| [`e4m-materials`](e4m-materials/) | 材料科学計算 | 組成変換（原子%/重量%/体積%）・体積・質量計算・元素物性 |
| [`e4m-data`](e4m-data/) | 外部データベース連携 | Materials Project・Starrydata 熱電材料データベース |

---

## クイックスタート

### 必要環境

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (推奨)

### インストール・起動例（e4m-materials）

```bash
cd e4m-materials
uv sync
uv run python -m e4m_materials
```

### Claude Code への組み込み

`~/.claude/settings.json` に追加：

```json
{
  "mcpServers": {
    "e4m-utils": {
      "command": "uv",
      "args": ["run", "python", "-m", "e4m_utils"],
      "cwd": "/path/to/e4m-mcp/e4m-utils"
    },
    "e4m-materials": {
      "command": "uv",
      "args": ["run", "python", "-m", "e4m_materials"],
      "cwd": "/path/to/e4m-mcp/e4m-materials"
    },
    "e4m-data": {
      "command": "uv",
      "args": ["run", "python", "-m", "e4m_data"],
      "env": {
        "MP_API_KEY": "your_materials_project_api_key"
      },
      "cwd": "/path/to/e4m-mcp/e4m-data"
    }
  }
}
```

---

## 各サーバーの詳細

### e4m-utils — 汎用ユーティリティ

| ツール | 説明 |
|-------|------|
| `e4m_convert_unit` | 物理単位変換（pint ベース） |
| `e4m_list_units` | 利用可能な単位一覧 |
| `e4m_doi2format` | DOI → 参考文献フォーマット変換 |
| `e4m_list_citation_styles` | 利用可能な引用スタイル一覧 |

### e4m-materials — 材料科学計算

| ツール | 説明 |
|-------|------|
| `e4m_at2wt` | 原子% → 重量% 変換 |
| `e4m_wt2at` | 重量% → 原子% 変換 |
| `e4m_vol2at` | 体積% → 原子% 変換 |
| `e4m_volume_rectangular` | 直方体の体積計算 |
| `e4m_volume_cylinder` | 円柱の体積計算 |
| `e4m_estimate_mass` | 体積・密度から質量推定 |
| `e4m_get_weigh` | 組成ごとの元素質量計算 |
| `e4m_get_element_properties` | 元素物性値の取得 |
| `e4m_list_element_properties` | 利用可能な物性プロパティ一覧 |
| `e4m_get_periodic_table` | 全周期表データ取得 |
| `e4m_get_atom_percent` | 組成式から原子% 計算 |

### e4m-data — 外部データベース連携

Materials Project の利用には API キーが必要です（[取得はこちら](https://next.materialsproject.org/)）。

| ツール | 説明 |
|-------|------|
| `e4m_get_mp_data` | Materials Project から物性データ取得 |
| `e4m_get_density` | 組成/MPID から密度取得 |
| `e4m_search_starrydata` | Starrydata 熱電材料データ検索 |
| `e4m_list_starrydata_props` | Starrydata の利用可能プロパティ一覧 |
| `e4m_download_starrydata` | Starrydata データセットのダウンロード |

#### 環境変数

```bash
# e4m-data/.env
MP_API_KEY=your_materials_project_api_key
```

---

## ドキュメント

- [機能カタログ](docs/mcp-feature-catalog.md) — 全ツール仕様・実装計画
- [MCP サーバー開発ガイド](docs/mcp-server-dev-guide.md) — 新しいサーバーの開発方法

---

## ライセンス

MIT
