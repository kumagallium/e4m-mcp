# MCP サーバー開発ガイド

**対象読者:** MCP サーバーを新規作成したい開発者
**前提知識:** Python の基本文法
**所要時間の目安:** 30〜60 分（初回）

---

## 目次

1. [MCP サーバーとは](#1-mcp-サーバーとは)
2. [ディレクトリ構造](#2-ディレクトリ構造)
3. [ファイルの作成手順](#3-ファイルの作成手順)
4. [ローカルでのテスト](#4-ローカルでのテスト)
5. [Registry への登録](#5-registry-への登録)
6. [チェックリスト](#6-チェックリスト)
7. [よくある質問](#7-よくある質問)

---

## 1. MCP サーバーとは

**MCP（Model Context Protocol）** は、AI モデル（Claude など）が外部ツールを呼び出すための標準プロトコルです。MCP サーバーを作ることで、Dify のエージェントから自作の計算・検索・変換ツールを使えるようになります。

Python の **FastMCP** ライブラリを使って実装します。

---

## 2. ディレクトリ構造

リポジトリ内の任意のディレクトリに、以下の構成でファイルを用意します。

```
your-server-name/            ← ハイフン区切りの英小文字
├── mcp.json                 ← サーバーのメタデータ（必須）
├── Dockerfile               ← コンテナのビルド手順（必須）
├── pyproject.toml           ← Python パッケージ設定（必須）
└── src/
    └── your_server_name/    ← アンダースコア区切り
        ├── __init__.py
        └── server.py        ← ツールの実装（必須）
```

> **参考実装:** `mcp-servers/e4m-utils/` が最もシンプルな実装例です。

---

## 3. ファイルの作成手順

### 3-1. `pyproject.toml`

Python パッケージとして定義します。

```toml
[project]
name = "my-server"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=1.3",
    "pydantic>=2.0",
    "uvicorn",
    "starlette",
    # 必要なライブラリを追加
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_server"]

[project.scripts]
my-server = "my_server.server:main"
```

---

### 3-2. `src/my_server/__init__.py`

空ファイルで問題ありません。

---

### 3-3. `src/my_server/server.py`

ツールを実装するメインファイルです。

```python
"""My Server — 〇〇計算ツール"""
from __future__ import annotations
import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

# FastMCP インスタンスを作成
mcp = FastMCP(
    name="my-server",
    instructions="〇〇計算ツール群。△△と□□を提供する。",
)

# ── ツール定義 ──────────────────────────────────────────────

@mcp.tool()
def calculate_something(
    value: Annotated[float, Field(description="入力値 (例: 3.14)")],
    unit: Annotated[str, Field(description="単位 (例: 'kg')")] = "kg",
) -> dict:
    """入力値に基づいて〇〇を計算する。"""
    result = value * 2  # 実際の計算処理に置き換える
    return {
        "input": value,
        "unit": unit,
        "result": result,
    }

# ── エントリポイント ────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="My Server MCP サーバー")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.environ.get("TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        # Docker 内部ネットワークからのアクセスを許可するために必要
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
```

#### ツール定義のポイント

| 要素 | 説明 |
|------|------|
| `@mcp.tool()` | デコレーターを付けると Dify からツールとして見える |
| 関数名 | 何をするか分かる名前をつける |
| 引数 | `Annotated[型, Field(description="...")]` で AI への説明を付ける |
| docstring | ツールの説明として AI に伝わる。1行で何をするか明確に書く |
| 戻り値 | `dict` / `str` / `list` いずれも可。必要な情報をすべて返す |

#### エラーハンドリング

```python
@mcp.tool()
def safe_calculation(value: Annotated[float, Field(description="入力値")]) -> dict:
    """エラーハンドリングの例。"""
    try:
        if value < 0:
            raise ValueError("value は 0 以上である必要があります")
        result = value ** 0.5
        return {"result": result}
    except ValueError:
        raise  # ValueError はそのまま再 raise（AI にエラー内容が伝わる）
    except Exception as e:
        raise ValueError(f"計算に失敗しました: {e}") from e
```

#### 環境変数（API キーなど）

```python
import os

API_KEY = os.environ.get("MY_API_KEY")

@mcp.tool()
def search_data(query: Annotated[str, Field(description="検索クエリ")]) -> dict:
    """外部 API を使うツールの例。"""
    if not API_KEY:
        raise ValueError("MY_API_KEY 環境変数が設定されていません")
    # API 呼び出し処理...
```

---

### 3-4. `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY my-server/pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .
COPY my-server/src/ src/
RUN pip install --no-cache-dir -e .
ENV TRANSPORT=sse
EXPOSE 8000
CMD ["python", "-m", "my_server", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
```

> **ビルドはリポジトリルートから実行します:**
> ```bash
> docker build -f my-server/Dockerfile -t e4m/my-server .
> ```

> **gcc が必要なライブラリ（pymatgen など）を使う場合:**
> ```dockerfile
> RUN apt-get update && apt-get install -y --no-install-recommends \
>     gcc g++ \
>     && rm -rf /var/lib/apt/lists/*
> ```
> を `pip install` の前に追加してください。

---

### 3-5. `mcp.json`

Registry がこのファイルを参照してコンテナを設定します。

```json
{
  "schema_version": "1.0",
  "name": "my-server",
  "display_name": "マイサーバー",
  "description": "〇〇計算と△△変換を提供する。",
  "version": "0.1.0",
  "author": "あなたの名前",
  "port": 8100,
  "transport": "sse",
  "health_check": "/sse",
  "dify": {
    "auto_register": true,
    "label": "マイサーバー",
    "icon": "🔬",
    "icon_background": "#E5F0FF"
  },
  "env": {
    "required": [],
    "optional": ["MY_API_KEY"]
  },
  "groups": [
    "default"
  ]
}
```

> **`port` について:** Registry UI からデプロイする場合は自動割り当てされます（手動設定不要）。手動で設定する場合は既存サーバーと重複しないようにしてください。

---

## 4. ローカルでのテスト

### 4-1. stdio モードで動作確認（最速）

```bash
cd your-server-name
pip install -e .
python -m my_server   # stdio モードで起動
```

起動後、標準入力に JSON-RPC を送れます（`Ctrl+C` で終了）。

### 4-2. SSE モードで起動して curl テスト

```bash
python -m my_server --transport sse --host 127.0.0.1 --port 8100
```

別ターミナルで:

```bash
# SSE 接続の確認（session_id が返れば OK）
curl -s --max-time 3 http://127.0.0.1:8100/sse
# → event: endpoint
# → data: /messages/?session_id=...
```

### 4-3. MCP Inspector（GUI ツール）

```bash
npx @modelcontextprotocol/inspector python -m my_server
```

ブラウザで `http://localhost:5173` を開くと、ツールの一覧確認・テスト実行ができます。

---

## 5. Registry への登録

### 5-1. GitHub にプッシュ

```bash
git add your-server-name/
git commit -m "新しい MCP サーバーを追加"
git push
```

### 5-2. Registry UI で登録

1. ブラウザで `http://10.0.0.1:8081` (VPN 接続必須) を開く
2. **「新規登録」** タブを選択
3. 以下を入力:

| 項目 | 必須 | 入力値 |
|------|------|-------|
| GitHub URL | ✅ | リポジトリの URL |
| ブランチ | | `main`（デフォルト） |
| サブディレクトリ | | サーバーのディレクトリパス（ルートの場合は空欄） |
| GitHub Token | プライベートの場合 | PAT を入力 |
| サーバー名・表示名など | | **mcp.json があれば自動補完**。ない場合は入力が必要 |

4. **「デプロイ」** をクリック
5. ログがリアルタイムで表示される。`デプロイ完了` が出れば成功

### 5-3. Dify で承認

1. Dify (`http://10.0.0.1`) にログイン
2. **ツール → MCP** タブを開く
3. 登録されたサーバーの **「承認」** をクリック
4. 承認が完了するとエージェントからツールを呼び出せるようになる

---

## 6. チェックリスト

デプロイ前に確認:

- [ ] すべての引数に `Field(description="...")` が付いている
- [ ] docstring が 1 行以上ある
- [ ] エラーは `ValueError` で返している（`raise Exception` ではなく）
- [ ] `mcp.json` の `port` が既存サーバーと重複していない
- [ ] `Dockerfile` の `CMD` のコマンド名が `pyproject.toml` のスクリプト名と一致している
- [ ] API キーはコードにハードコードせず `os.environ.get()` で取得している

---

## 7. よくある質問

### Q1. `enable_dns_rebinding_protection = False` が必要な理由は？

FastMCP v1.x はデフォルトで DNS リバインディング保護が有効です。Docker 内部ネットワーク (`172.20.x.x`) からのアクセス時に "Invalid Host header" エラーになるため、コンテナ内では無効化が必要です。

### Q2. `mcp.run()` の `host` / `port` 引数が使えない

FastMCP v1.26.0 以降では `mcp.run(host=, port=)` のキーワード引数が廃止されました。代わりに `mcp.settings.host` / `mcp.settings.port` を使ってください（上記のサンプルコード参照）。

### Q3. 外部 API を使うツールで API キーをどう渡す？

`mcp.json` の `env.optional` にキー名を記載しておくと、Registry UI の「環境変数」欄から入力できます。コンテナ起動時に環境変数として注入されます。

### Q4. ツールが Dify に表示されない

承認後にツールリストが更新されます。Dify のツール画面を**リロード**してから確認してください。それでも表示されない場合:

```bash
# コンテナが起動しているか
sudo docker ps | grep my-server

# SSE エンドポイントが応答するか
sudo docker exec docker-api-1 curl -s --max-time 3 http://<コンテナIP>:8000/sse
```

### Q5. デプロイに失敗する

Registry UI のログで原因を確認してください。よくある原因:

| エラー | 原因 | 対処 |
|-------|------|------|
| `git clone failed` | GitHub Token が未設定またはスコープ不足 | PAT の `repo` スコープを確認 |
| `pip install failed` | 依存ライブラリのビルドに gcc が必要 | Dockerfile に gcc インストールを追加 |
| `port already allocated` | ポートが使用中 | `mcp.json` の `port` を変更するか Registry UI で自動割り当てを使う |

---

*最終更新: 2026-03-11*
