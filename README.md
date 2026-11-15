# dataset-shugiin

Queria のデータセット `shugiin`（衆議院）のリポジトリです。データセットの説明は [docs/index.md](docs/index.md) にあります。

## ビルド

```bash
uv sync
scripts/build.sh
```

取得の間隔は 2 秒です。1 回のビルドで取得するのは 100 分（`GIAN_MAX_MINUTES`）までで、超えたら取得し終えた国会回次までで止め、残りは次のビルドで取得します。新しい国会から順に取得します。読み取りの規則を直したときは `GIAN_REFETCH=1` で公開中の国会回次もすべて取り直します。
