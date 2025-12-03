# Part of Odoo. See LICENSE file for full copyright and licensing details.
from psycopg2 import sql

from odoo import tools
from odoo import fields, models


class OdometerReport(models.Model):
    _name = 'fleet.vehicle.odometer.report'
    _description = "Fleet Odometer Analysis Report"
    _auto = False
    _order = 'recorded_date desc'

    vehicle_id = fields.Many2one('fleet.vehicle', "Vehicle", readonly=True)
    category_id = fields.Many2one(related='vehicle_id.category_id')
    model_id = fields.Many2one(related='vehicle_id.model_id')
    fuel_type = fields.Selection(related='vehicle_id.fuel_type')
    mileage_delta = fields.Float("Mileage Delta", readonly=True)
    odometer_value = fields.Float("Odometer Value", readonly=True)
    recorded_date = fields.Date('Date', readonly=True)

    def init(self):
        query = """
            -- Step 1: Cast vehicle_odometer timestamp
            WITH vehicle_odometer AS (
                SELECT odometer.vehicle_id, odometer.value, CAST(odometer.date AS TIMESTAMP) AS reading_date
                FROM fleet_vehicle_odometer odometer
            ),
            -- Step 2: Select only one odometer record (max value) per date per vehicle
            vehicle_odometer_single_date AS (
                SELECT DISTINCT ON (vehicle_id, reading_date) t.vehicle_id,  t.value, t.reading_date
                FROM vehicle_odometer t
                JOIN (
                    SELECT vehicle_id, reading_date, MAX(value) AS max_value
                    FROM vehicle_odometer
                    GROUP BY vehicle_id, reading_date
                ) t_max_val
                ON t.vehicle_id = t_max_val.vehicle_id AND t.reading_date = t_max_val.reading_date AND t.value = t_max_val.max_value
            ),
            -- Step 3: Get the acquisition date for each vehicle
            vehicle_odometer_acquisition AS (
                SELECT vehicle.id AS vehicle_id, odometer.value, reading_date, CAST(vehicle.acquisition_date AS TIMESTAMP)
                FROM vehicle_odometer_single_date odometer
                LEFT JOIN fleet_vehicle vehicle ON vehicle.id=odometer.vehicle_id
            ),
            -- Step 4: Add a fake odometer 0 value if the acquisition date is lower than other reading_dates (Interpolation)
            vehicle_odometer_start_pt AS (
                SELECT vehicle_id, reading_date, value, acquisition_date FROM vehicle_odometer_acquisition
                UNION ALL
                (
                    SELECT vehicle_id, acquisition_date AS reading_date, 0 AS value, acquisition_date
                    FROM vehicle_odometer_acquisition
                    GROUP BY vehicle_id, acquisition_date
                    HAVING acquisition_date < MIN(reading_date)
                )
                ORDER BY vehicle_id, reading_date, value DESC
            ),
            -- Step 5: Define the date range for each vehicle's odometer readings
            vehicle_odometer_date_range AS (
                SELECT
                    vehicle_id,
                    DATE_TRUNC('month', MIN(COALESCE(acquisition_date, reading_date))) AS start_date,
                    DATE_TRUNC('month', MAX(reading_date)) AS end_date
                FROM vehicle_odometer_start_pt
                GROUP BY vehicle_id
            ),
            -- Step 6: Compute the previous and next date and value for each odometer reading
            vehicle_odometer_prev_and_next AS (
                SELECT vehicle_id, reading_date, value,
                    LAG(reading_date) OVER (PARTITION BY vehicle_id ORDER BY reading_date) AS prev_date,
                    LAG(value) OVER (PARTITION BY vehicle_id ORDER BY reading_date) AS prev_val,
                    LEAD(reading_date) OVER (PARTITION BY vehicle_id ORDER BY reading_date) AS next_date,
                    LEAD(value) OVER (PARTITION BY vehicle_id ORDER BY reading_date) AS next_val
                FROM vehicle_odometer_start_pt
            ),
            -- Step 7: Generate a complete timeline list of months for each vehicle within the date range (empty value, prev* and next*)
            vehicle_odometer_timeline AS (
                SELECT
                    date_range.vehicle_id,
                    CAST(COALESCE(odometer.reading_date, generated_months.date) AS TIMESTAMP) AS date,
                    COALESCE(odometer.value, 0) AS value, -- Odometer value set to 0 if no reading exists
                    CAST(
                        FIRST_VALUE(COALESCE(odometer.reading_date, generated_months.date)) OVER (
                            PARTITION BY date_range.vehicle_id
                            ORDER BY generated_months.date
                        ) AS TIMESTAMP
                    ) AS min_date,
                    odometer.prev_date,
                    odometer.prev_val,
                    odometer.next_date,
                    odometer.next_val
                FROM vehicle_odometer_date_range AS date_range
                CROSS JOIN LATERAL GENERATE_SERIES(
                    date_range.start_date,
                    date_range.end_date,
                    '1 month'::INTERVAL
                ) generated_months (date)
                LEFT JOIN vehicle_odometer_prev_and_next AS odometer
                    ON date_range.vehicle_id = odometer.vehicle_id
                    AND generated_months.date = DATE_TRUNC('month', odometer.reading_date)
            ),
            -- Step 8: Fill Null previous/next dates for every newly added readings
            vehicle_odometer_prev_next_date AS (
                SELECT odometer.vehicle_id, odometer.date,
                MAX(COALESCE(odometer.prev_date, odo_prev_next.prev_date)) AS prev_date,
                MIN(COALESCE(odometer.next_date, odo_prev_next.next_date)) AS next_date
                FROM vehicle_odometer_timeline odometer
                LEFT JOIN vehicle_odometer_prev_and_next odo_prev_next
                    ON odometer.vehicle_id = odo_prev_next.vehicle_id
                    AND (odo_prev_next.prev_date IS NULL OR odo_prev_next.prev_date < odometer.date)
                    AND (odo_prev_next.next_date IS NULL OR odo_prev_next.next_date > odometer.date)
                GROUP BY odometer.vehicle_id, odometer.date
            ),
            -- Step 9: Fill Null previous/next values for every newly added readings & add strict previous date
            vehicle_odometer_prev_next_complete AS (
                SELECT DISTINCT
                    odo_dates.vehicle_id,
                    odo_dates.date,
                    odometer.min_date,
                    odometer.value,
                    odo_dates.prev_date,
                    odometer_prev.value AS prev_value,
                    odo_dates.next_date,
                    odometer_next.value AS next_value,
                    LAG(odo_dates.date) OVER (
                        PARTITION BY odo_dates.vehicle_id
                        ORDER BY odo_dates.date
                    ) AS strict_prev_date
                FROM vehicle_odometer_prev_next_date odo_dates
                LEFT JOIN vehicle_odometer_timeline odometer ON odo_dates.vehicle_id = odometer.vehicle_id AND odo_dates.date = odometer.date
                LEFT JOIN vehicle_odometer_timeline odometer_prev ON odo_dates.vehicle_id = odometer_prev.vehicle_id AND odo_dates.prev_date = odometer_prev.date
                LEFT JOIN vehicle_odometer_timeline odometer_next ON odo_dates.vehicle_id = odometer_next.vehicle_id AND odo_dates.next_date = odometer_next.date
            ),
            -- INTERPOLATION --
            -- Step 10: Interpolate to get raw_mileage_delta using previous and next known values
            vehicle_odometer_raw_delta AS (
                SELECT vehicle_id, date, value, strict_prev_date,
                    CASE
                        WHEN value = 0 AND prev_value IS NOT NULL AND next_value IS NOT NULL
                            THEN (next_value - prev_value) * (
                                EXTRACT(DAY FROM (date - strict_prev_date)) /
                                NULLIF(EXTRACT(DAY FROM (next_date - prev_date)), 0)
                            )
                        WHEN prev_value IS NULL THEN value
                        ELSE (value - prev_value) * (
                            EXTRACT(DAY FROM (date - strict_prev_date)) /
                            NULLIF(EXTRACT(DAY FROM (date - prev_date)), 0)
                        )
                    END AS raw_mileage_delta
                FROM vehicle_odometer_prev_next_complete
            ),
            -- Step 11: Interpolates values for missing months
            vehicle_odometer_interpolated AS (
                SELECT
                    vehicle_id,
                    date,
                    strict_prev_date,
                    CASE
                        WHEN value = 0 AND raw_mileage_delta IS NOT NULL
                            THEN SUM(raw_mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date)
                        ELSE value
                    END AS value
                FROM vehicle_odometer_raw_delta
            ),
            -- MONTHS WEIGHT --
            -- Step 12: Calculate the days span between every odometer's reading date
            vehicle_odometer_days_diff AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    value - COALESCE(LAG(value) OVER (PARTITION BY vehicle_id ORDER BY date), 0) AS raw_mileage_delta,
                    strict_prev_date,
                    EXTRACT(DAY FROM date::TIMESTAMP - LAG(date) OVER (PARTITION BY vehicle_id ORDER BY date)::TIMESTAMP) AS days_span
                FROM vehicle_odometer_interpolated
            ),
            -- Step 13: Compute weighted mileage for each month
            vehicle_odometer_weighted_mileage AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    raw_mileage_delta,
                    days_span,
                    DATE_TRUNC('month', strict_prev_date) AS prev_month,
                    DATE_TRUNC('month', date) AS current_month,
                    CASE
                        WHEN TO_CHAR(strict_prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN raw_mileage_delta
                        ELSE raw_mileage_delta * COALESCE(
                            (EXTRACT(DAY FROM date::TIMESTAMP - DATE_TRUNC('month', date)::TIMESTAMP) / NULLIF(days_span, 0)), 1
                        )
                    END AS current_month_mileage,
                    CASE
                        WHEN TO_CHAR(strict_prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN 0
                        ELSE raw_mileage_delta * (EXTRACT(DAY FROM DATE_TRUNC('month', date)::TIMESTAMP - strict_prev_date::TIMESTAMP) / NULLIF(days_span, 0))
                    END AS prev_month_mileage
                FROM vehicle_odometer_days_diff
            ),
            -- AGGREGATE --
            -- Step 14: Aggregate final results
            final_results AS (
                SELECT
                    vehicle_id,
                    date AS recorded_date,
                    SUM(mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date) AS odometer_value,
                    mileage_delta
                FROM (
                    SELECT vehicle_id, date, SUM(mileage_delta) AS mileage_delta
                    FROM (
                        SELECT vehicle_id, prev_month AS date, prev_month_mileage AS mileage_delta FROM vehicle_odometer_weighted_mileage WHERE prev_month IS NOT NULL
                        UNION ALL
                        SELECT vehicle_id, current_month AS date, current_month_mileage AS mileage_delta FROM vehicle_odometer_weighted_mileage
                    ) t
                    GROUP BY vehicle_id, date
                ) t
            ),
            -- Step 15: Handle the first recorded month with zero odometer
            min_month AS (
                SELECT vehicle_id, MIN(recorded_date) AS min_month_minus_one FROM final_results GROUP BY vehicle_id
            )
            -- Step 16: Generate final result set with a row number
            SELECT row_number() OVER () AS id, * FROM (
                SELECT vehicle_id, min_month_minus_one AS recorded_date, 0 AS odometer_value, 0 AS mileage_delta FROM min_month
                UNION ALL
                SELECT vehicle_id, recorded_date + INTERVAL '1 month' AS recorded_date, odometer_value, mileage_delta FROM final_results
                ORDER BY vehicle_id, recorded_date
            ) t
        """

        self.env.cr.execute(query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)))
