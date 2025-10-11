{base_filter}
{time_categories}

SELECT 
    EXTRACT(YEAR FROM filtered_datetime)::text AS year,
    SUM(is_past) AS "pastTrips",
    SUM(is_planned_future) AS "plannedFutureTrips",
    SUM(is_future) AS "futureTrips",
    SUM(trip_length * is_past) AS "pastKm",
    SUM(trip_length * is_planned_future) AS "plannedFutureKm",
    SUM(trip_length * is_future) AS "futureKm",
    SUM(trip_duration * is_past) AS "pastDuration",
    SUM(trip_duration * is_planned_future) AS "plannedFutureDuration",
    SUM(trip_duration * is_future) AS "futureDuration",
    SUM(carbon * is_past) AS "pastCO2",
    SUM(carbon * is_planned_future) AS "plannedFutureCO2",
    SUM(carbon * is_future) AS "futureCO2"
FROM time_categories
WHERE EXTRACT(YEAR FROM filtered_datetime) > 1950
AND EXTRACT(YEAR FROM filtered_datetime) < 2100
GROUP BY year

UNION ALL

SELECT 
    'future' AS year,
    0 AS "pastTrips",
    0 AS "plannedFutureTrips",
    SUM(is_future) AS "futureTrips",
    0 AS "pastKm",
    0 AS "plannedFutureKm",
    SUM(trip_length * is_future) AS "futureKm",
    0 AS "pastDuration",
    0 AS "plannedFutureDuration",
    SUM(trip_duration * is_future) AS "futureDuration",
    0 AS "pastCO2",
    0 AS "plannedFutureCO2",
    SUM(trip_duration * is_future) AS "futureCO2"
FROM time_categories
WHERE filtered_datetime IS NULL AND is_project = false
HAVING SUM(is_future) > 0

ORDER BY year;