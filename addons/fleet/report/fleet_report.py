# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class FleetVehicleCostReport(models.Model):
    _name = 'fleet.vehicle.cost.report'
    _description = "Fleet Analysis Report"
    _auto = False
    _order = 'date_start desc'

    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', readonly=True)
    name = fields.Char('Vehicle Name', readonly=True)
    driver_id = fields.Many2one('res.partner', 'Driver', readonly=True)
    fuel_type = fields.Char('Fuel', readonly=True)
    date_start = fields.Date('Date', readonly=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], readonly=True)
    service_type = fields.Many2one('fleet.service.type', 'Service Type', readonly=True)

    cost = fields.Float('Cost', readonly=True)
    cost_type = fields.Selection(string='Cost Type', selection=[
        ('contract', 'Contract'),
        ('service', 'Service')
    ], readonly=True)

    def init(self):
        query = """
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
        'service' AS cost_type,
        se.service_type_id AS service_type
    FROM
        fleet_vehicle ve
    JOIN
        fleet_vehicle_model vem ON vem.id = ve.model_id
    CROSS JOIN generate_series((
            SELECT
                min(date_from)
                FROM fleet_vehicle_log_services), CURRENT_DATE + '1 month'::interval, '1 month') d
        LEFT JOIN fleet_vehicle_log_services se ON se.vehicle_id = ve.id
            AND date_trunc('month', se.date_from) = date_trunc('month', d)
    WHERE
        ve.active AND se.active AND se.state != 'cancelled'
    GROUP BY
        ve.id,
        ve.company_id,
        vem.vehicle_type,
        ve.name,
        date_start,
        d,
        service_type
    ORDER BY
        ve.id,
        date_start
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
        COALESCE(cost_calc.total_cost, 0) AS cost,
        'contract' AS cost_type,
        cost_calc.cost_subtype_id AS service_type
    FROM
        fleet_vehicle ve
    JOIN
        fleet_vehicle_model vem ON vem.id = ve.model_id
    CROSS JOIN generate_series((
            SELECT
                min(acquisition_date)
                FROM fleet_vehicle), CURRENT_DATE + '1 month'::interval, '1 month') d
    LEFT JOIN LATERAL (
        SELECT
            c.cost_subtype_id,
            SUM(
                (CASE WHEN date_trunc('month', c.date) = date_trunc('month', d)
                      THEN COALESCE(c.amount, 0) ELSE 0 END) +
                (CASE WHEN c.cost_frequency = 'daily'
                           AND date_trunc('month', c.start_date) <= date_trunc('month', d)
                           AND date_trunc('month', c.expiration_date) >= date_trunc('month', d)
                      THEN c.cost_generated * extract(day FROM least(date_trunc('month', d) + interval '1 month', c.expiration_date) - greatest(date_trunc('month', d), c.start_date))
                      ELSE 0 END) +
                (CASE WHEN c.cost_frequency = 'monthly'
                           AND date_trunc('month', c.start_date) <= date_trunc('month', d)
                           AND date_trunc('month', c.expiration_date) >= date_trunc('month', d)
                      THEN c.cost_generated
                      ELSE 0 END) +
                (CASE WHEN c.cost_frequency = 'yearly'
                           AND d BETWEEN c.start_date AND c.expiration_date
                           AND date_part('month', c.date) = date_part('month', d)
                      THEN c.cost_generated
                      ELSE 0 END)
            ) AS total_cost
        FROM
            fleet_vehicle_log_contract c
        WHERE
            c.vehicle_id = ve.id
        GROUP BY c.cost_subtype_id
    ) cost_calc ON TRUE
    WHERE
        ve.active
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
    cost_type,
    service_type
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
        'service' as cost_type,
        service_type
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
            'contract' as cost_type,
            service_type
        FROM
            contract_costs cc)
) c
"""
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""CREATE or REPLACE VIEW %s as (%s)""", SQL.identifier(self._table), SQL(query)))
