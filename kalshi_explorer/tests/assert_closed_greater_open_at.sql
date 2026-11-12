select * from {{ref('stg_kalshi__markets')}}
where closed_at < opened_at
