{# 1 行 = 議案の本文のページ 1 つ（提出時法律案・要綱・修正案・決議案）。取得したページの行だけを入れ替える。
   1 つの修正案が複数の議案の一覧に載ることがあるので、主キーは本文の URL と議案 #}
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='text_url', on_schema_change='append_new_columns') }}

select *
from {{ ref('stg_texts') }}
