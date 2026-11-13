# 衆議院

衆議院が公開するデータを SQL で検索できるテーブルにしたデータセットです。今は衆議院ホームページの「議案」に載っている議案の審議経過を収録しています。

## 議案（bills）

[衆議院ホームページの「議案」](https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/menu.htm)に載っている、第142回国会（1998 年）からの議案の一覧と経過情報をテーブルにしたものです。法律案（閣法・衆法・参法）のほか、予算・条約・承認・承諾・決算・決議などを含みます。

| テーブル | 内容 |
| --- | --- |
| `bills.bills` | 1 行が 1 件の議案。最後に審議した国会での審議状況・付託委員会・審議結果・賛成会派と反対会派・公布年月日と法律番号 |
| `bills.bill_sessions` | 1 行が、1 つの国会で審議した 1 件の議案。継続審査になった議案は国会ごとに 1 行ずつあり、予備審査・付託の日付も持ちます |

- 議案は議案種類（`bill_type`）・提出回次（`submitted_session`）・議案番号（`bill_number`）で 1 件に決まります。番号の無い承諾・決算などと修正案は `bills.bill_sessions` だけにあります
- 成立した法律は `law_num`（例 令和七年法律第十三号）で e-Gov 法令検索のデータセットと結合できます。新しく制定した法律は `e_gov.laws.laws` の `law_num`、ほかの法律を改正する法律は `e_gov.laws.revisions` の `amendment_law_num` です
- 委員会の名前は「委員会」を除いた書き方です（例 財務金融）。会議録 `ndl.kokkai.meetings` と結合するときは「委員会」を付けます
- 議案の本文は収録せず、本文情報の URL（`honbun_url`）だけを持ちます
- 毎週、新しい 3 回分の国会の一覧と経過を取得し直します。それより前の国会は、まだ取得していない回次だけを取得します

## 使い方

国会ごとの閣法の成立件数:

```sql
SELECT submitted_session, count(*) AS bills, count(*) FILTER (WHERE status = '成立') AS passed
FROM shugiin.bills.bills
WHERE bill_type = '閣法'
GROUP BY submitted_session
ORDER BY submitted_session DESC;
```

成立した法律が改正した法令（e-Gov 法令検索）:

```sql
SELECT b.title AS bill, r.law_title AS amended_law, r.amendment_enforcement_date
FROM shugiin.bills.bills AS b
JOIN e_gov.laws.revisions AS r ON r.amendment_law_num = b.law_num
WHERE b.bill_type = '閣法' AND b.submitted_session = 217;
```

衆議院の付託委員会で議案を審査していた期間の会議録:

```sql
SELECT b.title, m.date, m.meeting_name, m.meeting_url
FROM shugiin.bills.bill_sessions AS b
JOIN ndl.kokkai.meetings AS m
  ON m.session = b.session
 AND m.house = '衆議院'
 AND m.meeting_name = b.shu_committee || '委員会'
 AND m.date BETWEEN b.shu_referred_date AND b.shu_committee_decided_date
WHERE b.bill_type = '閣法' AND b.submitted_session = 217 AND b.bill_number = 1
ORDER BY m.date;
```

## ビルド

```bash
uv sync
scripts/build.sh
```

取得の間隔は 2 秒です。1 回のビルドで取得するのは 100 分（`GIAN_MAX_MINUTES`）までで、超えたら取得し終えた国会回次までで止め、残りは次のビルドで取得します。新しい国会から順に取得します。読み取りの規則を直したときは `GIAN_REFETCH=1` で公開中の国会回次もすべて取り直します。

## 出典と利用条件

出典：衆議院ホームページ「議案」（https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/menu.htm）の議案の一覧と経過情報から、議案件名・日付・委員会・審議結果などの項目を取り出して作成したものです。

衆議院ホームページの内容の利用条件は「[リンク・著作権等について](https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/link.html)」に従います。
