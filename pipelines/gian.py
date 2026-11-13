"""衆議院ホームページの「議案」から、国会回次ごとの議案の一覧と審議経過を取得する。

国会回次ごとの一覧（kaiji<回次>.htm）に、その国会で審議した議案が種類別の表で載っている。
前の国会から継続審査になった議案は、審議した国会ごとに一覧に載り、経過のページもそれぞれにある。
1 行 = 1 つの国会で審議した 1 件の議案として、一覧の行と経過のページの項目を合わせて書く。

経過は国会の閉会後も公布日などが書き足されるので、新しい RECENT_SESSIONS 回分は毎回取り直す。
それより前の国会は、公開中の表にまだ無い回次だけを取得する。MAX_MINUTES 分を超えたら、
取得し終えた回次までで止める。GIAN_REFETCH=1 のときは公開中の回次も含めてすべて取り直す
（読み取りの規則を直したときに、古い回次へ反映するため）。経過のページが 404 の議案は、
一覧の項目だけを書く。

本文情報のある議案は、本文情報の一覧から提出時法律案・要綱・修正案のページをたどり、
本文を手を加えずにテキストにして書く（決議案は本文のページが直接ある）。

出力: data/gian/<回次>.ndjson.gz（議案）、data/gian/texts/<回次>.ndjson.gz（本文）

データソース: 衆議院ホームページ 議案情報
https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/menu.htm
"""

import gzip
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

from shared.fetch import fetch, replacing

logger = logging.getLogger("pipelines")

BASE = "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/"
USER_AGENT = "dataset-shugiin (+https://github.com/queria-io/dataset-shugiin)"
OUTPUT = Path("data/gian")
RECENT_SESSIONS = 3
# Sync の timeout_minutes (150) から dbt build と fdl commit・push の時間を引いた残り
MAX_MINUTES = int(os.environ.get("GIAN_MAX_MINUTES", "100"))
REFETCH = os.environ.get("GIAN_REFETCH") == "1"
# 1 ページずつ間を空ける
INTERVAL_SECONDS = 1.0

# 一覧の表の見出し → 議案種類。「決算その他」は行の先頭の列が種類
KINDS = {
    "衆法の一覧": "衆法", "参法の一覧": "参法", "閣法の一覧": "閣法", "予算の一覧": "予算",
    "条約の一覧": "条約", "承認の一覧": "承認", "承諾の一覧": "承諾", "決議の一覧": "決議",
    "規則の一覧": "規則", "規程の一覧": "規程", "議決の一覧": "議決", "決算その他": None,
}

# 経過のページの項目 → 列。「日付／値」の項目は 2 列に分ける
KEIKA = {
    "議案提出者": ["submitter"],
    "議案提出会派": ["submitter_groups"],
    "衆議院予備審査議案受理年月日": ["shu_preliminary_received"],
    "衆議院予備付託年月日／衆議院予備付託委員会": ["shu_preliminary_referred", "shu_preliminary_committee"],
    "衆議院議案受理年月日": ["shu_received"],
    "衆議院付託年月日／衆議院付託委員会": ["shu_referred", "shu_committee"],
    "衆議院審査終了年月日／衆議院審査結果": ["shu_committee_decided", "shu_committee_result"],
    "衆議院審議終了年月日／衆議院審議結果": ["shu_plenary_decided", "shu_plenary_result"],
    "衆議院審議時会派態度": ["shu_vote"],
    "衆議院審議時賛成会派": ["shu_yes_groups"],
    "衆議院審議時反対会派": ["shu_no_groups"],
    "参議院予備審査議案受理年月日": ["san_preliminary_received"],
    "参議院予備付託年月日／参議院予備付託委員会": ["san_preliminary_referred", "san_preliminary_committee"],
    "参議院議案受理年月日": ["san_received"],
    "参議院付託年月日／参議院付託委員会": ["san_referred", "san_committee"],
    "参議院審査終了年月日／参議院審査結果": ["san_committee_decided", "san_committee_result"],
    "参議院審議終了年月日／参議院審議結果": ["san_plenary_decided", "san_plenary_result"],
    "公布年月日／法律番号": ["promulgated", "law_number"],
    "議案提出者一覧": ["submitters"],
}


def get(path: str, not_found_ok: bool = False) -> str | None:
    body = fetch(BASE + path, user_agent=USER_AGENT, not_found_ok=not_found_ok)
    time.sleep(INTERVAL_SECONDS)
    if body is None:
        logger.warning("  404: %s", BASE + path)
        return None
    return body.decode("cp932", errors="replace")


def text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", html))).strip()


def sessions(pulldown: str) -> list[int]:
    """回次の選択肢（pulldown.htm）から、一覧のある国会回次を古い順に返す。"""
    return sorted({int(n) for n in re.findall(r'value="kaiji(\d+)\.htm"', pulldown)})


def list_rows(html: str, session: int) -> list[dict]:
    """国会回次の一覧のページから、議案の行を返す。見出しの無い表と見出しの知らない表は読まない。"""
    tables = re.finditer(r"<caption[^>]*>(.*?)</caption>(.*?)</table>", html, re.S | re.I)
    return [
        row
        for caption, body in ((text(m.group(1)), m.group(2)) for m in tables)
        if caption in KINDS
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I)
        if (row := list_row(caption, tr, session))
    ]


def list_row(caption: str, tr: str, session: int) -> dict | None:
    cells = [text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
    keika = re.search(r'href="\./keika/([^"]+)\.htm"', tr)
    if not cells or not keika:
        return None
    honbun = re.search(r'href="\./(honbun/[^"]+)"', tr)
    # 番号の無い表: 承諾は「提出回次・件名・状況」、決算その他は「種類・提出回次・件名・状況」
    kind, submitted, number, title, status = (
        (cells[0], cells[1], "", cells[2], cells[3]) if KINDS[caption] is None
        else (KINDS[caption], cells[0], "", cells[1], cells[2]) if caption == "承諾の一覧"
        else (KINDS[caption], cells[0], cells[1], cells[2], cells[3])
    )
    return {
        "session": session,
        "keika_id": keika.group(1),
        "bill_type": kind,
        "submitted_session": int(submitted) if submitted.isdigit() else None,
        "bill_number": int(number) if number.isdigit() else None,
        "title": title,
        "status": status or None,
        "keika_url": f"{BASE}keika/{keika.group(1)}.htm",
        "honbun_url": BASE + honbun.group(1) if honbun else None,
    }


def keika_fields(html: str) -> dict:
    """経過のページの項目を列に分ける。値の無い項目は None。

    項目は「項目・内容」の 2 列の行で、議案提出者一覧は headers 属性の無い別の表にあるので、
    表を問わず 2 列の行をすべて読む。
    """
    rows = (
        [text(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    )
    return {
        column: value or None
        for cells in rows
        if len(cells) == 2 and cells[0] in KEIKA
        for column, value in zip(KEIKA[cells[0]], split(cells[1], len(KEIKA[cells[0]])), strict=True)
    }


def document_links(index: str) -> list[tuple[str, str]]:
    """本文情報の一覧のページから、（見出し, honbun/ からのパス）を返す。"""
    return [
        (text(label), href)
        for href, label in re.findall(r'<a href="\./((?:houan|youkou|syuuseian)/[^"]+)"[^>]*>(.*?)</a>', index, re.S | re.I)
    ]


# 本文のページの置き場所 → 本文の種類
DOCUMENT_KINDS = {"houan": "提出時法律案", "youkou": "要綱", "syuuseian": "修正案", "ketsugian": "決議案"}


def document_kind(path: str) -> str:
    """honbun/ の下のフォルダから本文の種類を決める（見出しの書き方は回次で違うため）。"""
    return DOCUMENT_KINDS[path.split("/")[-2]]


def body_text(html: str) -> str:
    """本文のページから、見出しの後ろからフッターの前までを、改行を残したテキストにする。

    表（給与表など）は 1 行を 1 行に、セルをタブで区切る。行末の半角の空白と空の行だけを除き、
    全角の空白は残す。
    """
    main = re.search(r'id="TopContents"(.*?)<div id="FooterBlock"', html, re.S | re.I)
    body = (main.group(1) if main else "").split(">", 1)[-1]
    rows = re.sub(
        r"<tr[^>]*>(.*?)</tr>",
        lambda tr: "\t".join(text(td) for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr.group(1), re.S | re.I)) + "\n",
        body, flags=re.S | re.I,
    )
    lines = re.sub(r"<br[^>]*>|</p>|</h\d>", "\n", rows, flags=re.I)
    plain = unescape(re.sub(r"<[^>]+>", "", lines))
    return "\n".join(line.rstrip(" \t") for line in plain.splitlines() if line.strip(" \t\r"))


def documents(row: dict, published: set[str]) -> list[dict]:
    """1 件の議案の本文のページを取得する。本文情報が無い議案は空。

    本文は提出後に変わらないので、公開中の bills.texts にある本文のページ（published）は取得しない。
    """
    path = (row["honbun_url"] or "").removeprefix(BASE)
    if not path:
        return []
    resolution = "/ketsugian/" in path
    pages = (
        [(row["title"], path)] if resolution
        else [(label, "honbun/" + href) for label, href in document_links(get(path, not_found_ok=True) or "")]
    )
    return [
        {
            "bill_type": row["bill_type"], "submitted_session": row["submitted_session"],
            "bill_number": row["bill_number"], "document_kind": document_kind(href),
            "document_title": label, "text": body, "text_url": BASE + href, "honbun_url": row["honbun_url"],
        }
        for label, href in pages
        if BASE + href not in published
        if (page := get(href, not_found_ok=True)) and (body := page_text(href, page))
    ]


def page_text(href: str, page: str) -> str:
    """本文のページのテキスト。見出しかフッターが見つからず空になったページは書かない。"""
    body = body_text(page)
    if not body:
        logger.warning("  本文が読めない（ページの形が変わった？）: %s", BASE + href)
    return body


def law_num(promulgated: str | None, number: str | None) -> str | None:
    """公布日と法律番号から、e-Gov 法令検索と同じ書き方の法令番号（例 令和七年法律第十三号）を作る。"""
    era = re.match(r"(昭和|平成|令和)\s*(\d+)年", promulgated or "")
    if not era or not (number or "").isdigit():
        return None
    year = "元" if era.group(2) == "1" else kanji(int(era.group(2)))
    return f"{era.group(1)}{year}年法律第{kanji(int(number))}号"


def kanji(n: int) -> str:
    """1〜9999 を漢数字にする（例 107 → 百七）。"""
    digits = "〇一二三四五六七八九"
    return "".join(
        ("" if d == 1 and unit else digits[d]) + unit
        for d, unit in zip(map(int, f"{n:04d}"), ("千", "百", "十", ""))
        if d
    )


def split(raw: str, n: int) -> list[str]:
    parts = [p.strip() for p in raw.split("／")] if n > 1 else [raw]
    return (parts + [""] * n)[:n]


def published() -> tuple[set[int], set[str]]:
    """公開中の bills.bill_sessions にあり本文も取得済みの国会回次と、公開中の本文の URL。
    FDL_WORKING が無いか、表がまだ無ければ空。

    本文情報のある議案があるのに bills.texts に本文が 1 件も無い回次は、本文を取得する前に
    公開した回次なので、取得し直す。
    """
    working = os.environ.get("FDL_WORKING")
    if not working:
        return set(), set()
    import duckdb

    con = duckdb.connect(config={"custom_user_agent": os.environ.get("QUERIA_USER_AGENT", "")})
    con.execute("INSTALL ducklake; LOAD ducklake; INSTALL httpfs; LOAD httpfs;")
    con.execute(f"ATTACH 'ducklake:{working.replace(chr(39), chr(39) * 2)}' AS previous (READ_ONLY, META_TYPE 'sqlite')")
    try:
        sessions = {row[0] for row in con.sql(PUBLISHED_SESSIONS).fetchall()}
        texts = {row[0] for row in con.sql("select text_url from previous.bills.texts").fetchall()}
        return sessions, texts
    except duckdb.CatalogException as error:
        logger.info("  公開中の表が無い: %s", error)
        return set(), set()
    finally:
        con.close()


PUBLISHED_SESSIONS = """
select s.session
from previous.bills.bill_sessions as s
left join (select distinct honbun_url from previous.bills.texts) as t on t.honbun_url = s.honbun_url
group by s.session
having count(s.honbun_url) = 0 or count(t.honbun_url) > 0
"""


def sessions_to_fetch(available: list[int], published: set[int], has_catalog: bool) -> list[int]:
    """取得する国会回次を、新しい順に返す。PR のビルド確認は最新の 1 回だけ。"""
    newest = sorted(available, reverse=True)
    if not has_catalog:
        return newest[:1]
    return [s for i, s in enumerate(newest) if i < RECENT_SESSIONS or s not in published]


def fetch_session(session: int, fetched_at: str, output: Path, seen: set[str], published_texts: set[str]) -> int:
    rows = [
        {**row, **fields, "law_num": law_num(fields.get("promulgated"), fields.get("law_number")), "fetched_at": fetched_at}
        for row in list_rows(get(f"kaiji{session}.htm"), session)
        for page in [get(f"keika/{row['keika_id']}.htm", not_found_ok=True)]
        for fields in [keika_fields(page) if page else {}]
    ]
    if not rows:
        raise SystemExit(f"第{session}回国会の一覧に議案が無い（ページの形が変わった？）")
    # 継続審査の議案は前の国会と同じ本文のページを指すので、本文情報の URL ごとに 1 回だけ取得する。
    # seen はこの取得で先に（新しい国会で）取得した本文情報の URL
    unique = {row["honbun_url"]: row for row in rows if row["honbun_url"] and row["honbun_url"] not in seen}
    seen.update(unique)
    texts = [{**doc, "fetched_at": fetched_at} for row in unique.values() for doc in documents(row, published_texts)]
    write(output / f"{session}.ndjson.gz", rows)
    write(output / "texts" / f"{session}.ndjson.gz", texts)
    logger.info("  第%d回国会: %d 件、本文 %d 件", session, len(rows), len(texts))
    return len(rows)


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with replacing(path) as partial, gzip.open(partial, "wt", encoding="utf-8") as f:
        f.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def download_gian(output: Path = OUTPUT) -> int:
    has_catalog = bool(os.environ.get("FDL_WORKING"))
    published_sessions, published_texts = (set(), set()) if REFETCH else published()
    targets = sessions_to_fetch(sessions(get("pulldown.htm")), published_sessions, has_catalog)
    logger.info("  取得する国会回次: %s", targets)
    output.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat()
    deadline = time.monotonic() + MAX_MINUTES * 60
    total = 0
    seen: set[str] = set()
    for session in targets:
        total += fetch_session(session, fetched_at, output, seen, published_texts)
        if time.monotonic() > deadline:
            # 取得し終えた回次までを公開し、次のビルドで残りの回次を取得する
            logger.info("  %d 分を超えたので第%d回国会までで止める", MAX_MINUTES, session)
            break
    return total
