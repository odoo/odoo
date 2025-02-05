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
            -- Generate all first-of-the-month dates between the min and max date per vehicle_id. Used to interpolate the mileage delta for missing records.
            WITH date_series AS (
                SELECT DISTINCT vehicle_id,
                generate_series(
                    DATE_TRUNC('month', MIN(date)),
                    DATE_TRUNC('month', MAX(date)),
                    '1 month'::interval
                ) AS date
                FROM fleet_vehicle_odometer
                GROUP BY vehicle_id
            ),
            -- Compute the complete set of odometer records, with missing months
            complete_fleet_vehicle_odometer AS (
                SELECT vehicle_id, date, value FROM fleet_vehicle_odometer
                UNION ALL
                (
                    SELECT ds.vehicle_id, ds.date, 0 as value
                    FROM date_series ds
                    LEFT JOIN fleet_vehicle_odometer fvo
                        ON ds.vehicle_id = fvo.vehicle_id
                        AND ds.date = DATE_TRUNC('month', fvo.date)
                    WHERE fvo.date IS NULL
                )
            ),
            -- Compute the min date for each vehicle
            fleet_vehicle_odometer_min_date AS (
                SELECT t1.vehicle_id, t1.date, t1.value, t2.min_date
                FROM complete_fleet_vehicle_odometer t1
                JOIN (
                    SELECT vehicle_id, MIN(date) AS min_date
                    FROM complete_fleet_vehicle_odometer
                    GROUP BY vehicle_id
                ) t2 ON t1.vehicle_id = t2.vehicle_id
            ),
            -- Compute the previous and next dates and values for each record
            fleet_vehicle_odometer_previous_next AS (
                SELECT t1.vehicle_id, t1.date, t1.value,
                        (SELECT date FROM fleet_vehicle_odometer_min_date t2
                            WHERE t2.vehicle_id = t1.vehicle_id
                            AND t2.date < t1.date
                            ORDER BY t2.date DESC
                            LIMIT 1
                    ) AS prev_date,
                        (SELECT date FROM fleet_vehicle_odometer_min_date t2
                            WHERE t2.vehicle_id = t1.vehicle_id
                            AND t2.date < t1.date AND (t2.value <> 0 OR t2.date=t1.min_date)
                            ORDER BY t2.date DESC
                            LIMIT 1
                    ) AS prev_date_with_nonull_value,
                        (SELECT value FROM fleet_vehicle_odometer_min_date t2
                            WHERE t2.vehicle_id = t1.vehicle_id
                            AND t2.date < t1.date AND (t2.value <> 0 OR t2.date=t1.min_date)
                            ORDER BY t2.date DESC
                            LIMIT 1
                    ) AS prev_value,
                    (SELECT date FROM fleet_vehicle_odometer_min_date t2
                        WHERE t2.vehicle_id = t1.vehicle_id
                        AND t2.date > t1.date AND t2.value <> 0
                        ORDER BY t2.date ASC
                        LIMIT 1
                    ) AS next_date,
                    (SELECT value FROM fleet_vehicle_odometer_min_date t2
                        WHERE t2.vehicle_id = t1.vehicle_id
                        AND t2.date > t1.date AND t2.value <> 0
                        ORDER BY t2.date ASC
                        LIMIT 1
                    ) AS next_value
                FROM fleet_vehicle_odometer_min_date t1
            ),
            -- Compute raw mileage delta by doing a weighted average
            fleet_vehicle_odometer_values_filled AS (
                SELECT vehicle_id, date, value,
                    CASE
                        WHEN value = 0 AND prev_value IS NOT NULL AND next_value IS NOT NULL THEN
                            (next_value - prev_value) * ((EXTRACT(DAY FROM (date - prev_date)) / EXTRACT(DAY FROM (next_date - INTERVAL '1 day' - prev_date_with_nonull_value))))
                        ELSE
                            (value - prev_value) * ((EXTRACT(DAY FROM (date - prev_date)) / EXTRACT(DAY FROM (date - INTERVAL '1 DAY' - prev_date_with_nonull_value))))
                    END AS raw_mileage_delta
                FROM fleet_vehicle_odometer_previous_next
            ),
            -- Compute the odometer values for the add fields for missing months
            fleet_vehicle_odometer_values_filled_sum AS (
                SELECT vehicle_id, date,
                CASE
                    WHEN value = 0 AND raw_mileage_delta IS NOT NULL THEN
                        SUM(raw_mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date)
                    ELSE value
                END AS value
                FROM fleet_vehicle_odometer_values_filled
            ),
            -- Compute the raw mileage delta between every odometer record ordered by date
            raw_mileage_delta AS (
                SELECT vehicle_id, date, value,
                    value - LAG(value) OVER (PARTITION BY vehicle_id ORDER BY date) AS raw_mileage_delta
                FROM fleet_vehicle_odometer_values_filled_sum
            ),
            -- Compute the previous record date
            previous_record_dates_prev_date AS (
                SELECT vehicle_id, date, value, raw_mileage_delta,
                    LAG(date) OVER (PARTITION BY vehicle_id ORDER BY date) AS prev_date
                FROM raw_mileage_delta
            ),
            -- Compute the days span between the previous record date and the record date
            days_span AS (
                SELECT vehicle_id, date, value, raw_mileage_delta, prev_date,
                    EXTRACT(DAY FROM date::timestamp - prev_date::timestamp) AS days_span
                FROM previous_record_dates_prev_date
            ),
            -- Compute the weighted average distance per month
            weighted_mileage_delta AS (
                SELECT vehicle_id, date, value, raw_mileage_delta, prev_date, days_span,
                    DATE_TRUNC('month', prev_date) AS prev_month,
                    DATE_TRUNC('month', date) AS current_month,
                    CASE
                        WHEN TO_CHAR(prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN raw_mileage_delta
                        ELSE raw_mileage_delta * (EXTRACT(DAY FROM date::timestamp - DATE_TRUNC('month', date)::timestamp) / NULLIF(days_span, 0))
                    END AS current_month_mileage,
                    CASE
                        WHEN TO_CHAR(prev_date, 'YYYY-MM') = TO_CHAR(date, 'YYYY-MM') THEN 0
                        ELSE raw_mileage_delta * (EXTRACT(DAY FROM DATE_TRUNC('month', date)::timestamp - prev_date::timestamp) / NULLIF(days_span, 0))
                    END AS prev_month_mileage
                FROM days_span
            ),
            -- Compute the final mileage delta per month
            weighted_mileage_delta_combined AS (
                SELECT vehicle_id, prev_month AS date, SUM(prev_month_mileage) AS mileage_delta
                FROM (
                    SELECT vehicle_id, value, prev_month, prev_month_mileage FROM weighted_mileage_delta
                    UNION ALL
                    SELECT vehicle_id, value, current_month, current_month_mileage FROM weighted_mileage_delta
                ) AS t
                WHERE prev_month IS NOT NULL
                GROUP BY vehicle_id, prev_month
            ),
            -- Add the interpolated odometer values
            weighted_mileage_delta_combined_values AS (
                SELECT t1.vehicle_id, t1.date AS recorded_date, t1.mileage_delta, t2.odometer_value
                FROM weighted_mileage_delta_combined t1
                JOIN (
                    SELECT vehicle_id, date, SUM(mileage_delta) OVER (PARTITION BY vehicle_id ORDER BY date) AS odometer_value
                    FROM weighted_mileage_delta_combined t2
                ) AS t2 ON t1.vehicle_id = t2.vehicle_id AND t1.date = t2.date
            )
            SELECT ROW_NUMBER() OVER () AS id, vehicle_id, recorded_date, odometer_value, mileage_delta
            FROM weighted_mileage_delta_combined_values
            ORDER BY vehicle_id, recorded_date
        """

        self.env.cr.execute(query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)))
