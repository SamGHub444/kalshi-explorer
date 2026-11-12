with source as (
    select * from {{ source('kalshi', 'events') }}
)

,renamed as (
    select
        loaded_at,
        json_value(payload, '$.event_ticker') as event_id,
        json_value(payload, '$.category') as category,
        json_value(payload, '$.product_metadata.competition') as competition,
        json_value(payload, '$.series_ticker') as series_id,
        json_value(payload, '$.title') as event_name,
        cast(json_value(payload, '$.mutually_exclusive') as boolean) as mutually_exclusive,
    from source
)

select * from renamed