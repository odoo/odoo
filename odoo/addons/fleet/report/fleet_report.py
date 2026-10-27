# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from psycopg2 import sql

from odoo import tools
from odoo import api, fields, models


class FleetReport(models.Model):
    _name = "fleet.vehicle.cost.report"
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
contract_costs AS (
    SELECT
        ve.id AS vehicle_id,
        ve.company_id AS company_id,
        ve.name AS name,
        ve.driver_id AS driver_id,
        ve.fuel_type AS fuel_type,
        date(date_trunc('month', d)) AS date_start,
        vem.vehicle_type as vehicle_type,
        (COALESCE(sum(co.amount), 0) + COALESCE(sum(cod.cost_generated * extract(day FROM least (date_trunc('month', d) + interval '1 month', cod.expiration_date) - greatest (date_trunc('month', d), cod.start_date))), 0) + COALESCE(sum(com.cost_generated), 0) + COALESCE(sum(coy.cost_generated), 0)) AS
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
        LEFT JOIN fleet_vehicle_log_contract co ON co.vehicle_id = ve.id
            AND date_trunc('month', co.date) = date_trunc('month', d)
        LEFT JOIN fleet_vehicle_log_contract cod ON cod.vehicle_id = ve.id
            AND date_trunc('month', cod.start_date) <= date_trunc('month', d)
            AND date_trunc('month', cod.expiration_date) >= date_trunc('month', d)
            AND cod.cost_frequency = 'daily'
    LEFT JOIN fleet_vehicle_log_contract com ON com.vehicle_id = ve.id
        AND date_trunc('month', com.start_date) <= date_trunc('month', d)
        AND date_trunc('month', com.expiration_date) >= date_trunc('month', d)
        AND com.cost_frequency = 'monthly'
    LEFT JOIN fleet_vehicle_log_contract coy ON coy.vehicle_id = ve.id
        AND d BETWEEN coy.start_date and coy.expiration_date
        AND date_part('month', coy.date) = date_part('month', d)
        AND coy.cost_frequency = 'yearly'
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
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            ))
