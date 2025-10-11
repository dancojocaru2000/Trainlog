{base_filter}
{time_categories}
{split_material}

SELECT 
    CASE 
        WHEN :tripType IN ('air', 'helicopter') AND a.iata IS NOT NULL 
        THEN a.manufacturer || ' ' || a.model
        ELSE m.material_type
    END AS material,
    SUM(m.is_past) AS "pastTrips",
    SUM(m.is_planned_future) AS "plannedFutureTrips",
    SUM(m.is_past + m.is_planned_future) AS "totalTrips",
    SUM(m.trip_length * m.is_past) AS "pastKm",
    SUM(m.trip_length * m.is_planned_future) AS "plannedFutureKm",
    SUM(m.trip_length * (m.is_past + m.is_planned_future)) AS "totalKm",
    SUM(m.trip_duration * m.is_past) AS "pastDuration",
    SUM(m.trip_duration * m.is_planned_future) AS "plannedFutureDuration",
    SUM(m.trip_duration * (m.is_past + m.is_planned_future)) AS "totalDuration",
    SUM(m.carbon * m.is_past) AS "pastCO2",
    SUM(m.carbon * m.is_planned_future) AS "plannedFutureCO2",
    SUM(m.carbon * (m.is_past + m.is_planned_future)) AS "totalCO2"
FROM split_material m
LEFT JOIN airliners a ON m.material_type = a.iata
GROUP BY material
ORDER BY "totalTrips" DESC;