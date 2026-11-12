
select * from {{ref('stg_kalshi__markets')}}
where result in ('yes','no')
and settlement_value != if(result = 'yes', 1, 0)
