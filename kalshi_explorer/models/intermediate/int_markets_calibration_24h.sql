with markets as (
    select 
    market_id,
    event_id,
    opened_at,
    closed_at,
    market_name,
    outcome_name,
    prev_yes_bid,
    prev_yes_ask,
    market_volume,
    settlement_value
    from {{ ref('stg_kalshi__markets') }}
    where 1=1
    and result != 'scalar'
    and market_volume >= {{ var('min_volume', 1) }}
    and timestamp_diff(closed_at,opened_at,hour) >= 24
    and prev_yes_bid > 0
    and prev_yes_ask < 1
    {# and prev_yes_ask - prev_yes_bid <= {{ var('max_spread', 0.1) }} #}


),

events as (
    select
    event_id,
    category,
    competition,
    series_id,
    event_name,
    mutually_exclusive
    from {{ ref('stg_kalshi__events') }}
),

series as (
    select
    series_id,
    frequency,
    series_name
    from {{ ref('stg_kalshi__series') }}
)

select 
m.market_id,
m.opened_at,
m.closed_at,
m.settlement_value,
(m.prev_yes_bid+m.prev_yes_ask)/2 as yes_prob_day_before,
e.event_id,
e.category,
e.competition,
m.market_name,
m.outcome_name,
e.event_name,
e.mutually_exclusive,
s.series_id,
s.frequency,
s.series_name
from markets m 
left join events e on m.event_id = e.event_id
left join series s on e.series_id = s.series_id