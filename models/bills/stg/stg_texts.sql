{# 1 行 = 議案の本文のページ 1 つ。継続審査の議案は複数の国会回次で同じページを取得するので、議案ごとに 1 つにする #}

select *
from {{ ref('raw_texts') }}
qualify row_number() over (partition by text_url, bill_type, submitted_session, bill_number order by fetched_at desc) = 1
