{# 「令和 7年 3月31日」のような和暦の日付を DATE にする。読めない値は NULL #}
{% macro wareki_date(column) %}
    try(make_date(
        case regexp_extract({{ column }}, '^(昭和|平成|令和)', 1)
            when '昭和' then 1925
            when '平成' then 1988
            when '令和' then 2018
        end + cast(regexp_extract({{ column }}, '(\d+)\s*年', 1) as integer),
        cast(regexp_extract({{ column }}, '(\d+)\s*月', 1) as integer),
        cast(regexp_extract({{ column }}, '(\d+)\s*日', 1) as integer)
    ))
{% endmacro %}
