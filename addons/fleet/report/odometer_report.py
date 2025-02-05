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
            WITH vehicle_odometer_date_range AS (
                SELECT
                    vehicle_id,
                    Cast(Date_trunc('month', Min(date)) AS TIMESTAMP) AS start_date,
                    Cast(Date_trunc('month', Max(date)) AS TIMESTAMP) AS end_date
                FROM
                    fleet_vehicle_odometer
                GROUP BY
                    vehicle_id
            ),
            vehicle_odometer_date_range_min_date AS (
                SELECT
                    date_range.vehicle_id,
                    Cast(
                        COALESCE(odometer.date, generated_months.date) AS TIMESTAMP
                    ) AS date,
                    COALESCE(odometer.value, 0) AS value,
                    Cast(
                        First_value(COALESCE(odometer.date, generated_months.date)) OVER (
                            partition BY date_range.vehicle_id
                            ORDER BY
                                generated_months.date
                        ) AS TIMESTAMP
                    ) AS min_date
                FROM
                    vehicle_odometer_date_range DATE_RANGE
                    CROSS JOIN lateral generate_series(
                        date_range.start_date,
                        date_range.end_date,
                        '1 month' :: interval
                    ) generated_months (date)
                    LEFT JOIN fleet_vehicle_odometer odometer ON date_range.vehicle_id = odometer.vehicle_id
                    AND generated_months.date = date_trunc('month', odometer.date)
            ),
            vehicle_monthly_odometer AS (
                SELECT
                    vehicle_id,
                    date,
                    min_date,
                    value,
                    lag(date) OVER (
                        partition BY vehicle_id
                        ORDER BY
                            date
                    ) AS previous_date,
                    max(
                        CASE
                            WHEN value > 0
                            OR (
                                value = 0
                                AND date = min_date
                            ) THEN date
                        END
                    ) OVER (
                        partition BY vehicle_id
                        ORDER BY
                            date rows BETWEEN UNBOUNDED PRECEDING
                            AND 1 PRECEDING
                    ) AS last_valid_odometer
                FROM
                    vehicle_odometer_date_range_min_date
            ),
            vehicle_odometer_filled_gaps AS (
                SELECT
                    current_odometer.vehicle_id,
                    current_odometer.date,
                    current_odometer.value,
                    prev_odometer.date AS prev_date,
                    prev_odometer.value AS prev_value,
                    next_odometer.date AS next_date,
                    next_odometer.value AS next_value,
                    CASE
                        WHEN current_odometer.value = 0
                        AND prev_odometer.value IS NOT NULL
                        AND next_odometer.value IS NOT NULL THEN (next_odometer.value - prev_odometer.value) * (
                            extract(
                                day
                                FROM
                                    (
                                        current_odometer.date - current_odometer.previous_date
                                    )
                            ) / extract(
                                day
                                FROM
                                    (
                                        next_odometer.date - current_odometer.last_valid_odometer
                                    )
                            )
                        )
                        WHEN prev_odometer.value IS NULL THEN current_odometer.value
                        ELSE (
                            current_odometer.value - prev_odometer.value
                        ) * (
                            extract(
                                day
                                FROM
                                    (
                                        current_odometer.date - current_odometer.previous_date
                                    )
                            ) / extract(
                                day
                                FROM
                                    (
                                        current_odometer.date - current_odometer.last_valid_odometer
                                    )
                            )
                        )
                    END AS raw_mileage_delta
                FROM
                    vehicle_monthly_odometer current_odometer
                    LEFT JOIN lateral (
                        SELECT
                            DISTINCT ON (
                                odometer.vehicle_id
                            ) odometer.date,
                            odometer.value,
                            last_valid_odometer
                        FROM
                            vehicle_monthly_odometer odometer
                        WHERE
                            odometer.vehicle_id = current_odometer.vehicle_id
                            AND odometer.date < current_odometer.date
                            AND (
                                odometer.value <> 0
                                OR (
                                    odometer.value = 0
                                    AND current_odometer.min_date = current_odometer.previous_date
                                )
                            )
                        ORDER BY
                            odometer.vehicle_id,
                            odometer.date DESC
                    ) AS prev_odometer ON true
                    LEFT JOIN lateral (
                        SELECT
                            DISTINCT ON (
                                odometer.vehicle_id
                            ) odometer.date,
                            odometer.value
                        FROM
                            vehicle_monthly_odometer odometer
                        WHERE
                            odometer.vehicle_id = current_odometer.vehicle_id
                            AND odometer.date > current_odometer.date
                            AND odometer.value <> 0
                        ORDER BY
                            odometer.vehicle_id,
                            odometer.date ASC
                    ) AS next_odometer ON true
            ),
            vehicle_odometer_interpolated AS (
                SELECT
                    vehicle_id,
                    date,
                    CASE
                        WHEN value = 0
                        AND raw_mileage_delta IS NOT NULL THEN sum(raw_mileage_delta) OVER (
                            partition BY vehicle_id
                            ORDER BY
                                date
                        )
                        ELSE value
                    END AS value
                FROM
                    vehicle_odometer_filled_gaps
            ),
            vehicle_odometer_days_diff AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    value - COALESCE(lag(value) OVER (
                        partition BY vehicle_id
                        ORDER BY
                            date
                    ), 0) AS raw_mileage_delta,
                    lag(
                        date
                    ) OVER (
                        partition BY vehicle_id
                        ORDER BY
                            date
                    ) AS prev_date,
                    extract(
                        day
                        FROM
                            date :: timestamp - lag(date) OVER (
                                partition BY vehicle_id
                                ORDER BY
                                    date
                            ) :: timestamp
                    ) AS days_span
                FROM
                    vehicle_odometer_interpolated
            ),
            vehicle_weighted_mileage AS (
                SELECT
                    vehicle_id,
                    date,
                    value,
                    raw_mileage_delta,
                    prev_date,
                    days_span,
                    date_trunc('month', prev_date) AS prev_month,
                    date_trunc('month', date) AS current_month,
                    CASE
                        WHEN to_char(prev_date, 'YYYY-MM') = to_char(date, 'YYYY-MM') THEN raw_mileage_delta
                        ELSE raw_mileage_delta * COALESCE((
                            extract(
                                day
                                FROM
                                    date :: timestamp - date_trunc('month', date) :: timestamp
                            ) / NULLIF(days_span, 0)
                        ), 1)
                    END AS current_month_mileage,
                    CASE
                        WHEN to_char(prev_date, 'YYYY-MM') = to_char(date, 'YYYY-MM') THEN 0
                        ELSE raw_mileage_delta * (
                            extract(
                                day
                                FROM
                                    date_trunc('month', date) :: timestamp - prev_date :: timestamp
                            ) / NULLIF(days_span, 0)
                        )
                    END AS prev_month_mileage
                FROM
                    vehicle_odometer_days_diff
            ),
            final_results AS (
                SELECT
                    vehicle_id,
                    date AS recorded_date,
                    sum(mileage_delta) OVER (
                        partition BY vehicle_id
                        ORDER BY
                            date
                    ) AS odometer_value,
                    mileage_delta
                FROM
                    (
                        SELECT
                            vehicle_id,
                            date,
                            sum(mileage_delta) AS mileage_delta
                        FROM
                            (
                                SELECT
                                    vehicle_id,
                                    prev_month AS date,
                                    prev_month_mileage AS mileage_delta
                                FROM
                                    vehicle_weighted_mileage
                                WHERE
                                    prev_month IS NOT NULL
                                UNION
                                ALL
                                SELECT
                                    vehicle_id,
                                    current_month AS date,
                                    current_month_mileage AS mileage_delta
                                FROM
                                    vehicle_weighted_mileage
                            ) t
                        GROUP BY
                            vehicle_id,
                            date
                    ) t
            ),
            min_month AS (
                SELECT vehicle_id, MIN(recorded_date) AS min_month_minus_one
                FROM final_results
                GROUP BY vehicle_id
            )
            SELECT row_number() OVER () AS id, * FROM (
                SELECT vehicle_id, min_month_minus_one AS recorded_date, 0 AS odometer_value, 0 AS mileage_delta
                FROM min_month
                UNION ALL
                SELECT
                    vehicle_id,
                    recorded_date + INTERVAL '1 month' AS recorded_date,
                    odometer_value,
                    mileage_delta
                FROM final_results
                ORDER BY vehicle_id, recorded_date
            ) t
        """

        self.env.cr.execute(query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)))
