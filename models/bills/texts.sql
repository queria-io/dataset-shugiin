{# 1 行 = 議案の本文のページ 1 つ（提出時法律案・要綱・修正案・決議案）。取得したページの行だけを入れ替える。
   継続審査の議案は複数の国会回次で同じページを取得するので、議案ごとに 1 つにする。
   1 つの修正案が複数の議案の一覧に載ることがあるので、主キーは本文の URL と議案 #}
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='text_url', on_schema_change='append_new_columns') }}

select *
from read_json(
    'data/gian/texts/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        bill_type: 'VARCHAR', submitted_session: 'INTEGER', bill_number: 'INTEGER', document_kind: 'VARCHAR',
        document_title: 'VARCHAR', text: 'VARCHAR', text_url: 'VARCHAR', honbun_url: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
qualify row_number() over (partition by text_url, bill_type, submitted_session, bill_number order by fetched_at desc) = 1
