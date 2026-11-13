-- 議案は種類・提出回次・番号で 1 件に決まる
select bill_type, submitted_session, bill_number from {{ ref('bills') }} group by all having count(*) > 1
