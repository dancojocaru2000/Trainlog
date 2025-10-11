{base_filter}
{time_categories}

SELECT 
    countries,
    trip_length,
    trip_duration,
    carbon,
    is_past AS "past",
    is_planned_future AS "plannedFuture"
FROM time_categories
WHERE is_project IS FALSE
