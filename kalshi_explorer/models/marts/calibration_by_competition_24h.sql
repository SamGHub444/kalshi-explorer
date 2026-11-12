with markets as (
    select *
    from {{ ref('int_markets_calibration_24h') }}
)

,bucketed as (
    select
    market_id,
    market_name,
    category,
    competition,
    floor(yes_prob_day_before * 10) / 10  as probability_bucket,  -- 6.734 → 6 → 0.6
    yes_prob_day_before,
    settlement_value
    from markets
)

,aggregated as (
    select 
    category,
    competition,
    probability_bucket,
    avg(yes_prob_day_before) as average_predicted_probability,
    avg(settlement_value) as actual_yes_rate,
    avg(settlement_value) - avg(yes_prob_day_before) as calibration_error,
    count(market_id) as sample_size
    from bucketed
    group by category, competition, probability_bucket
    
)

select *
from aggregated