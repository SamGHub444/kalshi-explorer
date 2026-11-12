with source as (
    select * from {{ source('kalshi', 'markets') }}
)

,renamed as (
    select
        loaded_at,
        json_value(payload, '$.ticker') as market_id,
        json_value(payload, '$.event_ticker') as event_id,
        cast(json_value(payload, '$.open_time') as timestamp) as opened_at,
        cast(json_value(payload, '$.close_time') as timestamp) as closed_at,
        cast(json_value(payload, '$.created_time') as timestamp) as created_at,
        cast(json_value(payload, '$.updated_time') as timestamp) as updated_at,
        cast(json_value(payload, '$.settlement_ts') as timestamp) as settlement_at,
        json_value(payload, '$.result') as result,
        json_value(payload, '$.market_type') as market_type,
        json_value(payload, '$.title') as market_name,
        json_value(payload, '$.yes_sub_title') as outcome_name,
        cast(json_value(payload, '$.previous_yes_bid_dollars') as numeric) as prev_yes_bid,
        cast(json_value(payload, '$.previous_yes_ask_dollars') as numeric) as prev_yes_ask,
        cast(json_value(payload, '$.previous_price_dollars') as numeric) as prev_price,
        cast(json_value(payload, '$.volume_fp') as numeric) as market_volume,
        cast(json_value(payload, '$.settlement_value_dollars') as numeric) as settlement_value,
    from source
)

select * from renamed

