{# 取得した議案 (data/gian/*.ndjson.gz) を型を付けて読む #}
{{ config(materialized='ephemeral') }}

select *
from read_json(
    'data/gian/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        session: 'INTEGER', keika_id: 'VARCHAR', bill_type: 'VARCHAR', submitted_session: 'INTEGER',
        bill_number: 'INTEGER', title: 'VARCHAR', status: 'VARCHAR', keika_url: 'VARCHAR', honbun_url: 'VARCHAR',
        submitter: 'VARCHAR', submitter_groups: 'VARCHAR', submitters: 'VARCHAR',
        shu_preliminary_received: 'VARCHAR', shu_preliminary_referred: 'VARCHAR', shu_preliminary_committee: 'VARCHAR',
        shu_received: 'VARCHAR', shu_referred: 'VARCHAR', shu_committee: 'VARCHAR',
        shu_committee_decided: 'VARCHAR', shu_committee_result: 'VARCHAR',
        shu_plenary_decided: 'VARCHAR', shu_plenary_result: 'VARCHAR',
        shu_vote: 'VARCHAR', shu_yes_groups: 'VARCHAR', shu_no_groups: 'VARCHAR',
        san_preliminary_received: 'VARCHAR', san_preliminary_referred: 'VARCHAR', san_preliminary_committee: 'VARCHAR',
        san_received: 'VARCHAR', san_referred: 'VARCHAR', san_committee: 'VARCHAR',
        san_committee_decided: 'VARCHAR', san_committee_result: 'VARCHAR',
        san_plenary_decided: 'VARCHAR', san_plenary_result: 'VARCHAR',
        promulgated: 'VARCHAR', law_number: 'VARCHAR', law_num: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
