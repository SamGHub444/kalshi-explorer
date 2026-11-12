with source as (
    select * from {{ source('kalshi', 'series') }}
)

,renamed as (
    select
        loaded_at,
        json_value(payload, '$.ticker') as series_id,
        json_value(payload, '$.frequency') as frequency,
        json_value(payload, '$.title') as series_name,
    from source
)

select * from renamed