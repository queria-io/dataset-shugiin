{# 取得した議案の本文 (data/gian/texts/*.ndjson.gz)。pipelines が書いた項目をそのまま読む #}

select *
from read_json(
    'data/gian/texts/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        bill_type: 'VARCHAR', submitted_session: 'INTEGER', bill_number: 'INTEGER', document_kind: 'VARCHAR',
        document_title: 'VARCHAR', text: 'VARCHAR', text_url: 'VARCHAR', honbun_url: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
