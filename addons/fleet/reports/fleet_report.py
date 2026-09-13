from odoo import fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.libs.sql import SQL

COST_REPORT_QUERY = """
WITH service_costs AS (
    SELECT
        ve.id AS vehicle_id,
        ve.company_id AS company_id,
        ve.name AS name,
        ve.driver_id AS driver_id,
        ve.fuel_type AS fuel_type,
        date(date_trunc('month', d)) AS date_start,
        vem.vehicle_type as vehicle_type,
        COALESCE(sum(se.amount), 0) AS
        COST,
        'service' AS cost_type
    FROM
        fleet_vehicle ve
    JOIN
        fleet_vehicle_model vem ON vem.id = ve.model_id
    CROSS JOIN generate_series((
            SELECT
                min(date)
                FROM fleet_vehicle_log_services), CURRENT_DATE + '1 month'::interval, '1 month') d
        LEFT JOIN fleet_vehicle_log_services se ON se.vehicle_id = ve.id
            AND date_trunc('month', se.date) = date_trunc('month', d)
    WHERE
        ve.active AND se.active AND se.state != 'cancelled'
    GROUP BY
        ve.id,
        ve.company_id,
        vem.vehicle_type,
        ve.name,
        date_start,
        d
    ORDER BY
        ve.id,
        date_start
),
contract_month AS (
    -- One row per (contract, month). The costs used to be gathered by joining
    -- fleet_vehicle_log_contract three times, once per frequency, under a
    -- single GROUP BY: every extra contract row multiplied every sum, so a
    -- vehicle with two monthly contracts of 100 reported 400 and three
    -- reported 900. Aggregating per contract first and joining the result once
    -- is what makes each contract count exactly once.
    SELECT
        co.vehicle_id AS vehicle_id,
        date_trunc('month', d) AS month_start,
        CASE
            WHEN date_trunc('month', co.date) = date_trunc('month', d)
                THEN COALESCE(co.amount, 0)
            ELSE 0
        END
        + CASE
            WHEN co.repeat_unit IS NULL
                 OR COALESCE(co.repeat_interval, 0) <= 0
                 OR co.start_date IS NULL
                THEN 0
            WHEN co.repeat_unit = 'day'
                THEN COALESCE(co.cost_generated, 0) * cov.days
                     / co.repeat_interval
            WHEN co.repeat_unit = 'week'
                THEN COALESCE(co.cost_generated, 0) * cov.days
                     / (7.0 * co.repeat_interval)
            WHEN co.repeat_unit = 'month'
                THEN COALESCE(co.cost_generated, 0) * cov.days
                     / (cov.month_days * co.repeat_interval)
            WHEN co.repeat_unit = 'year'
                THEN COALESCE(co.cost_generated, 0) * cov.days
                     / (365.25 * co.repeat_interval)
            ELSE 0
        END AS cost
    FROM
        fleet_vehicle_log_contract co
    CROSS JOIN generate_series((
            SELECT
                min(acquisition_date)
                FROM fleet_vehicle), CURRENT_DATE + '1 month'::interval, '1 month') d
    CROSS JOIN LATERAL (
        -- Days of this month the contract actually covers, and the length of
        -- the month to measure them against. A recurring cost is prorated by
        -- that fraction, so a contract starting mid-month contributes half.
        SELECT
            GREATEST(0, EXTRACT(epoch FROM
                LEAST(
                    date_trunc('month', d) + interval '1 month',
                    COALESCE(
                        co.expiration_date::timestamp + interval '1 day',
                        date_trunc('month', d) + interval '1 month')
                )
                - GREATEST(
                    date_trunc('month', d),
                    COALESCE(co.start_date::timestamp, date_trunc('month', d)))
            ) / 86400.0) AS days,
            EXTRACT(day FROM
                date_trunc('month', d) + interval '1 month' - interval '1 day'
            ) AS month_days
    ) cov
    WHERE
        date_trunc('month', co.date) = date_trunc('month', d)
        OR (
            co.start_date IS NOT NULL
            AND date_trunc('month', co.start_date) <= date_trunc('month', d)
            AND date_trunc('month', COALESCE(
                    co.expiration_date,
                    CURRENT_DATE + interval '100 years')) >= date_trunc('month', d)
        )
),
contract_costs AS (
    SELECT
        ve.id AS vehicle_id,
        ve.company_id AS company_id,
        ve.name AS name,
        ve.driver_id AS driver_id,
        ve.fuel_type AS fuel_type,
        date(date_trunc('month', d)) AS date_start,
        vem.vehicle_type as vehicle_type,
        COALESCE(sum(cm.cost), 0) AS
        COST,
        'contract' AS cost_type
    FROM
        fleet_vehicle ve
    JOIN
        fleet_vehicle_model vem ON vem.id = ve.model_id
    CROSS JOIN generate_series((
            SELECT
                min(acquisition_date)
                FROM fleet_vehicle), CURRENT_DATE + '1 month'::interval, '1 month') d
    LEFT JOIN contract_month cm ON cm.vehicle_id = ve.id
        AND cm.month_start = date_trunc('month', d)
    WHERE
        ve.active
    GROUP BY
        ve.id,
        ve.company_id,
        vem.vehicle_type,
        ve.name,
        date_start,
        d
    ORDER BY
        ve.id,
        date_start
)
SELECT row_number() OVER (ORDER BY vehicle_id ASC) as id,
    company_id,
    vehicle_id,
    name,
    driver_id,
    fuel_type,
    date_start,
    vehicle_type,
    COST,
    cost_type
FROM (
    SELECT
        company_id,
        vehicle_id,
        name,
        driver_id,
        fuel_type,
        date_start,
        vehicle_type,
        COST,
        'service' as cost_type
    FROM
        service_costs sc
    UNION ALL (
        SELECT
            company_id,
            vehicle_id,
            name,
            driver_id,
            fuel_type,
            date_start,
            vehicle_type,
            COST,
            'contract' as cost_type
        FROM
            contract_costs cc)
) c
"""


class FleetVehicleCostReport(models.Model):
    _name = "fleet.vehicle.cost.report"
    _description = "Fleet Analysis Report"
    _auto = False
    _order = "date_start desc"

    company_id = fields.Many2one("res.company", readonly=True)
    vehicle_id = fields.Many2one("fleet.vehicle", readonly=True)
    name = fields.Char("Vehicle Name", readonly=True)
    driver_id = fields.Many2one("res.partner", readonly=True)
    fuel_type = fields.Char("Fuel", readonly=True)
    date_start = fields.Date("Date", readonly=True)
    vehicle_type = fields.Selection([("car", "Car"), ("bike", "Bike")], readonly=True)

    cost = fields.Float(readonly=True)
    cost_type = fields.Selection(
        selection=[("contract", "Contract"), ("service", "Service")],
        readonly=True,
    )

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            SQL(
                """CREATE or REPLACE VIEW %s as (%s)""",
                SQL.identifier(self._table),
                SQL(COST_REPORT_QUERY),
            )
        )
