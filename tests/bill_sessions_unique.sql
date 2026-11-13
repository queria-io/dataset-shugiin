-- 1 つの国会で同じ経過のページが 2 回載らない
select session, keika_id from {{ ref('bill_sessions') }} group by all having count(*) > 1
