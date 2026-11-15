{# 1 行 = 1 つの国会で審議した 1 件の議案。取得した国会回次の行だけを入れ替える #}
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='session', on_schema_change='append_new_columns') }}

select *
from {{ ref('stg_bill_sessions') }}
