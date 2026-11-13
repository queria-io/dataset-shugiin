{# 1 行 = 1 件の議案。番号のある議案について、最後に審議した国会の行を残す #}
select
    bill_type,
    submitted_session,
    bill_number,
    title,
    session as last_session,
    status,
    submitter,
    submitter_groups,
    submitters,
    shu_received_date,
    shu_committee,
    shu_committee_result,
    shu_plenary_decided_date,
    shu_plenary_result,
    shu_vote,
    shu_yes_groups,
    shu_no_groups,
    san_received_date,
    san_committee,
    san_committee_result,
    san_plenary_decided_date,
    san_plenary_result,
    promulgated_date,
    law_number,
    law_num,
    keika_url,
    honbun_url
from {{ ref('bill_sessions') }}
where bill_number is not null
-- 回付案は元の議案と同じ国会・同じ番号で別の行になる。元の議案の行を残し、残りは経過の ID の順で決める
qualify row_number() over (
    partition by bill_type, submitted_session, bill_number
    order by session desc, contains(status, '回付案'), keika_id
) = 1
