"""衆議院が公開するデータのパイプライン。

1. gian: 衆議院ホームページの議案の一覧と審議経過を取得する
2. dbt: 取得した国会回次の行を入れ替える
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines.gian import download_gian

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        if not dbt.invoke(command).success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def download() -> None:
    logger.info("1/2: gian (議案)")
    download_gian()


def main():
    download()
    logger.info("2/2: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
