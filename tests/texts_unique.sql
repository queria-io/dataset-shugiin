-- 本文のページは議案ごとに 1 行
select text_url, bill_type, submitted_session, bill_number from {{ ref('texts') }} group by all having count(*) > 1
