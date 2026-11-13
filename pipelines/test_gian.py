import unittest

from pipelines.gian import keika_fields, kanji, law_num, list_rows, sessions, sessions_to_fetch

LIST = """
<table><caption class="txt04b">閣法の一覧</caption>
<tr><th>提出回次</th><th>番号</th><th>議案件名</th><th>審議状況</th><th>経過情報</th><th>本文情報</th></tr>
<tr valign="top"><td>217</td><td>1</td><td>所得税法等の一部を改正する法律案</td><td>成立</td>
<td><a href="./keika/1DDE0CA.htm">経過</a></td><td><a href="./honbun/g21709001.htm">本文</a></td></tr>
<tr valign="top"><td>217</td><td><br></td><td>所得税法等の一部を改正する法律案に対する修正案</td><td>本院議了</td>
<td><a href="./keika/1DDE0CE.htm">経過</a></td><td><br></td></tr>
</table>
<table><caption class="txt04b">承諾の一覧</caption>
<tr><td>216</td><td>令和六年度一般会計予備費使用総調書</td><td>衆議院で閉会中審査</td><td><a href="./keika/1DDE100.htm">経過</a></td></tr>
</table>
<table><caption class="txt04b">決算その他</caption>
<tr><td>決算</td><td>217</td><td>令和五年度一般会計歳入歳出決算</td><td>衆議院で閉会中審査</td><td><a href="./keika/1DDE200.htm">経過</a></td></tr>
</table>
"""

KEIKA = """
<TR valign=top><TD class="td" headers="KOMOKU">議案提出者</TD><TD class="td" headers="NAIYO">内閣</TD></TR>
<TR valign=top><TD class="td" headers="KOMOKU">衆議院付託年月日／衆議院付託委員会</TD>
<TD class="td" headers="NAIYO">令和 7年 2月14日<BR>／<BR>財務金融</TD></TR>
<TR valign=top><TD class="td" headers="KOMOKU">衆議院審議時賛成会派</TD><TD class="td" headers="NAIYO">自由民主党; 公明党</TD></TR>
<TR valign=top><TD class="td" headers="KOMOKU">公布年月日／法律番号</TD><TD class="td" headers="NAIYO">／</TD></TR>
</TABLE>
<table border="1" width="100%" class="table">
<TR valign=top>
<TD width="40%" class="td"><span class="txt03">議案提出者一覧</span></TD>
<TD width="60%" class="td"><span class="txt03">森田俊和君; 山井和則君</span></TD>
</TR>
</TABLE>
"""


class ListRowsTest(unittest.TestCase):
    def test_reads_bills_amendments_and_unnumbered_tables(self):
        rows = list_rows(LIST, 217)
        self.assertEqual(
            [(r["bill_type"], r["submitted_session"], r["bill_number"], r["keika_id"]) for r in rows],
            [("閣法", 217, 1, "1DDE0CA"), ("閣法", 217, None, "1DDE0CE"), ("承諾", 216, None, "1DDE100"), ("決算", 217, None, "1DDE200")],
        )
        self.assertTrue(rows[0]["honbun_url"].endswith("/honbun/g21709001.htm"))
        self.assertIsNone(rows[1]["honbun_url"])


class KeikaFieldsTest(unittest.TestCase):
    def test_splits_date_and_value(self):
        fields = keika_fields(KEIKA)
        self.assertEqual(fields["submitter"], "内閣")
        self.assertEqual((fields["shu_referred"], fields["shu_committee"]), ("令和 7年 2月14日", "財務金融"))
        self.assertEqual(fields["shu_yes_groups"], "自由民主党; 公明党")
        self.assertEqual((fields["promulgated"], fields["law_number"]), (None, None))
        self.assertEqual(fields["submitters"], "森田俊和君; 山井和則君")


class LawNumTest(unittest.TestCase):
    def test_formats_like_e_gov(self):
        self.assertEqual(law_num("令和 7年 3月31日", "13"), "令和七年法律第十三号")
        self.assertEqual(law_num("令和 1年 5月 1日", "1"), "令和元年法律第一号")
        self.assertEqual(law_num("平成10年 6月15日", "107"), "平成十年法律第百七号")
        self.assertIsNone(law_num(None, None))

    def test_kanji(self):
        self.assertEqual([kanji(n) for n in (10, 20, 111, 1001)], ["十", "二十", "百十一", "千一"])


class SessionsTest(unittest.TestCase):
    def test_reads_pulldown(self):
        self.assertEqual(sessions('<OPTION value="kaiji222.htm">第222回</OPTION><OPTION value="kaiji142.htm">'), [142, 222])

    def test_fetches_recent_and_unpublished(self):
        available = list(range(142, 223))
        published = set(range(142, 220)) - {150}
        self.assertEqual(sessions_to_fetch(available, published, True), [222, 221, 220, 150])
        self.assertEqual(sessions_to_fetch(available, set(), False), [222])


if __name__ == "__main__":
    unittest.main()
