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
            -- Step 1: Get the acquisition date for each vehicle
            WITH vehicle_odometer AS (
                SELECT vehicle.id AS vehicle_id, odometer.value, CAST(odometer.date AS TIMESTAMP), CAST(vehicle.acquisition_date AS TIMESTAMP)
                FROM fleet_vehicle_odometer odometer
                LEFT JOIN fleet_vehicle vehicle ON vehicle.id=odometer.vehicle_id
            ),
            -- Step 2: Select only one odometer record (with max value) per date per vehicle
            vehicle_odometer_single_date AS (
                SELECT DISTINCT ON (vehicle_id, date) t.vehicle_id, t.date, t.value, t.acquisition_date
                FROM vehicle_odometer t
                JOIN (
                    SELECT vehicle_id, date, MAX(value) AS max_value
                    FROM vehicle_odometer
                    GROUP BY vehicle_id, date
                ) t_max_val
                ON t.vehicle_id = t_max_val.vehicle_id AND t.date = t_max_val.date AND t.value = t_max_val.max_value
            ),
            -- Step 3: Create a fake odometer reading at 0km if the acquisition date is set and lower than every other reading
            vehicle_odometer_acquisition_date AS (
                SELECT vehicle_id, date, value, acquisition_date FROM vehicle_odometer_single_date
                UNION ALL
                (
                    SELECT vehicle_id, acquisition_date AS date, 0 AS value, acquisition_date
                    FROM vehicle_odometer_single_date
                    GROUP BY vehicle_id, acquisition_date
                    HAVING acquisition_date < MIN(date)
                )
            ),
            -- Step 4: Compute the previous and next date and value for each odometer reading
            vehicle_odometer_prev_and_next AS (
                SELECT vehicle_id, date, value, acquisition_date,
                    LAG(date) OVER (PARTITION BY vehicle_id ORDER BY date) AS prev_date,
                    LAG(value) OVER (PARTITION BY vehicle_id ORDER BY date) AS prev_val,
                    LEAD(date) OVER (PARTITION BY vehicle_id ORDER BY date) AS next_date,
                    LEAD(value) OVER (PARTITION BY vehicle_id ORDER BY date) AS next_val
                FROM vehicle_odometer_acquisition_date
            ),
            -- Step 5: Define the date range for each vehicle's odometer readings
            vehicle_odometer_date_range AS (
                SELECT
                    vehicle_id,
                    COALESCE(
                        CAST(DATE_TRUNC('month', MIN(acquisition_date)) AS TIMESTAMP),
                        CAST(DATE_TRUNC('month', MIN(date)) AS TIMESTAMP)) AS start_date,
                    CAST(DATE_TRUNC('month', MAX(date)) AS TIMESTAMP) AS end_date
                FROM vehicle_odometer_prev_and_next
                GROUP BY vehicle_id
            ),
            -- Step 6: Generate a complete list of months for each vehicle within the date range (empty value, prev* and next*)
            vehicle_odometer_date_range_min_date AS (
                SELECT
                    date_range.vehicle_id,
                    CAST(COALESCE(odometer.date, generated_months.date) AS TIMESTAMP) AS date,
                    COALESCE(odometer.value, 0) AS value, -- Odometer value set to 0 if no reading exists
                    CAST(
                        FIRST_VALUE(COALESCE(odometer.date, generated_months.date)) OVER (
                            PARTITION BY date_range.vehicle_id
                            ORDER BY generated_months.date
                        ) AS TIMESTAMP
                    ) AS min_date,
                    odometer.prev_date,
                    odometer.prev_val,
                    odometer.next_date,
                    odometer.next_val
                FROM vehicle_odometer_date_range date_range
                CROSS JOIN LATERAL GENERATE_SERIES(
                    date_range.start_date,
                    date_range.end_date,
                    '1 month'::INTERVAL
                ) generated_months (date)
                LEFT JOIN vehicle_odometer_prev_and_next odometer
                    ON date_range.vehicle_id = odometer.vehicle_id
                    AND generated_months.date = DATE_TRUNC('month', odometer.date)
            ),
            -- Step 7: Compute the previous/next dates for every newly added readings
            vehicle_odometer_prev_next_date AS (
                SELECT odometer.vehicle_id, odometer.date,
                MAX(COALESCE(odometer.prev_date, odo_prev_next.prev_date)) AS prev_date,
                MIN(COALESCE(odometer.next_date, odo_prev_next.next_date)) AS next_date
                FROM vehicle_odometer_date_range_min_date odometer
                LEFT JOIN vehicle_odometer_prev_and_next odo_prev_next
                    ON odometer.vehicle_id = odo_prev_next.vehicle_id
                    AND (odo_prev_next.prev_date IS NULL OR odo_prev_next.prev_date < odometer.date)
                    AND (odo_prev_next.next_date IS NULL OR odo_prev_next.next_date > odometer.date)
                GROUP BY odometer.vehicle_id, odometer.date
            ),
            -- Step 8: Compute the previous/next values for every newly added readings
            vehicle_odometer_prev_next_complete AS (
                SELECT DISTINCT
                    odo_dates.vehicle_id,
                    odo_dates.date,
                    odometer.min_date,
                    odometer.value,
                    odo_dates.prev_date,
                    odometer_prev.value AS prev_value,
                    odo_dates.next_date,
                    odometer_next.value AS next_value
                FROM vehicle_odometer_prev_next_date odo_dates
                LEFT JOIN vehicle_odometer_date_range_min_date odometer ON odo_dates.vehicle_id = odometer.vehicle_id AND odo_dates.date = odometer.date
                LEFT JOIN vehicle_odometer_date_range_min_date odometer_prev ON odo_dates.vehicle_id = odometer_prev.vehicle_id AND odo_dates.prev_date = odometer_prev.date
                LEFT JOIN vehicle_odometer_date_range_min_date odometer_next ON odo_dates.vehicle_id = odometer_next.vehicle_id AND odo_dates.next_date = odometer_next.date
            ),
            -- Step 9: Compute the strict previous date for each odometer reading
            vehicle_odometer_strict_prev AS (
                SELECT vehicle_id, date, min_date, value, prev_date, prev_value, next_date, next_value,
                    LAG(date) OVER (
                        PARTITION BY vehicle_id
                        ORDER BY date
                    ) AS strict_previous_date
                FROM vehicle_odometer_prev_next_complete
            ),
            -- Step 9: Fill in gaps (interpolate) in odometer readings using previous and next known values
            vehicle_odometer_filled_gaps AS (
                SELECT vehicle_id, date, value,
                    CASE
                        WHEN value = 0 AND prev_value IS NOT NULL AND next_value IS NOT NULL
                            THEN (next_value - prev_value) * (
                                EXTRACT(DAY FROM (date - strict_previous_date)) /
                                NULLIF(EXTRACT(DAY FROM (next_date - prev_date)), 0)
                            )
                        WHEN prev_value IS NULL THEN value
                        ELSE (value - prev_value) * (
                            EXTRACT(DAY FROM (date - strict_previous_date)) /
                            NULLIF(EXTRACT(DAY FROM (date - prev_date)), 0)
                        )
                    END AS raw_mileage_delta
                FROM vehicle_odometer_strict_prev
            ),
            -- Step 10: Sum the interpolated mileage delta values to have an odometer per month
            vehicle_odometer_interpolated AS (
                SELECT
                    vehicle_id,
                    date,
                    CASE
                        WHEN value = 0 AND raw_mileage_delta IS NOT NULL
                            THEN SUM(raw_mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date)
                        ELSE value
                    END AS value
                FROM vehicle_odometer_filled_gaps
            ),
            -- Step 11: Calculate the days span between every odometer's reading date
            vehicle_odometer_days_diff AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    value - COALESCE(LAG(value) OVER (PARTITION BY vehicle_id ORDER BY date), 0) AS raw_mileage_delta,
                    LAG(date) OVER (PARTITION BY vehicle_id ORDER BY date) AS prev_date,
                    EXTRACT(DAY FROM date::TIMESTAMP - LAG(date) OVER (PARTITION BY vehicle_id ORDER BY date)::TIMESTAMP) AS days_span
                FROM vehicle_odometer_interpolated
            ),
            -- Step 12: Compute weighted mileage for each month
            vehicle_weighted_mileage AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    raw_mileage_delta,
                    prev_date,
                    days_span,
                    DATE_TRUNC('month', prev_date) AS prev_month,
                    DATE_TRUNC('month', date) AS current_month,
                    CASE
                        WHEN TO_CHAR(prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN raw_mileage_delta
                        ELSE raw_mileage_delta * COALESCE(
                            (EXTRACT(DAY FROM date::TIMESTAMP - DATE_TRUNC('month', date)::TIMESTAMP) / NULLIF(days_span, 0)), 1
                        )
                    END AS current_month_mileage,
                    CASE
                        WHEN TO_CHAR(prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN 0
                        ELSE raw_mileage_delta * (EXTRACT(DAY FROM DATE_TRUNC('month', date)::TIMESTAMP - prev_date::TIMESTAMP) / NULLIF(days_span, 0))
                    END AS prev_month_mileage
                FROM vehicle_odometer_days_diff
            ),
            -- Step 13: Aggregate final results
            final_results AS (
                SELECT
                    vehicle_id,
                    date AS recorded_date,
                    SUM(mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date) AS odometer_value,
                    mileage_delta
                FROM (
                    SELECT vehicle_id, date, SUM(mileage_delta) AS mileage_delta
                    FROM (
                        SELECT vehicle_id, prev_month AS date, prev_month_mileage AS mileage_delta FROM vehicle_weighted_mileage WHERE prev_month IS NOT NULL
                        UNION ALL
                        SELECT vehicle_id, current_month AS date, current_month_mileage AS mileage_delta FROM vehicle_weighted_mileage
                    ) t
                    GROUP BY vehicle_id, date
                ) t
            ),
            -- Step 14: Handle the first recorded month with zero odometer
            min_month AS (
                SELECT vehicle_id, MIN(recorded_date) AS min_month_minus_one FROM final_results GROUP BY vehicle_id
            )
            -- Step 15: Generate final result set with a row number
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
