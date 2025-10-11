{base_filter}
{time_categories}
{split_operators}

SELECT 
    operator,
    SUM(is_past) AS "pastTrips",
    SUM(is_planned_future) AS "plannedFutureTrips",
    SUM(is_past + is_planned_future) AS "totalTrips",
    SUM(trip_length * is_past) AS "pastKm",
    SUM(trip_length * is_planned_future) AS "plannedFutureKm",
    SUM(trip_length * (is_past + is_planned_future)) AS "totalKm",
    SUM(trip_duration * is_past) AS "pastDuration",
    SUM(trip_duration * is_planned_future) AS "plannedFutureDuration",
    SUM(trip_duration * (is_past + is_planned_future)) AS "totalDuration",
    SUM(carbon * is_past) AS "pastCO2",
    SUM(carbon * is_planned_future) AS "plannedFutureCO2",
    SUM(carbon * (is_past + is_planned_future)) AS "totalCO2"
FROM split_operators
GROUP BY operator
ORDER BY "totalTrips" DESC;