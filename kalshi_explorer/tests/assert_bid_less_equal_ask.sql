
select * from {{ref('stg_kalshi__markets')}}
where prev_yes_bid > prev_yes_ask
