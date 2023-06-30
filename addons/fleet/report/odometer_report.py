# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from psycopg2 import sql

from odoo import tools
from odoo import fields, models


class OdometerReport(models.Model):
    _name = "fleet.vehicle.odometer.report"
    _description = "Fleet Odometer Analysis Report"
    _auto = False
    _order = 'recorded_date desc'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', readonly=True)
    name = fields.Char('Name')
    category_id = fields.Many2one(related="vehicle_id.category_id")
    monthly_km = fields.Float('Monthly Kilometers', readonly=True)
    recorded_date = fields.Date('Date')

    def init(self):
        query = """
                SELECT sum(f.difference) as monthly_km,
                       f.vehicle_id as vehicle_id,
                       f.name as name,
                       date(date_trunc('month', f.date)) AS recorded_date
                FROM
                (SELECT
                  t1.vehicle_id,
                  t1.name,
                  t1.value - t2.value AS difference,
                  t1.date
                FROM
                  fleet_vehicle_odometer t1
                JOIN
                  fleet_vehicle_odometer t2 ON t1.vehicle_id = t2.vehicle_id
                  AND t1.date > t2.date
                LEFT JOIN
                  fleet_vehicle_odometer t3 ON t1.vehicle_id = t3.vehicle_id
                  AND t3.date > t2.date
                  AND t3.date < t1.date
                WHERE
                  t3.date IS NULL
                ORDER BY
                  t1.vehicle_id, t1.date) as f
                GROUP BY
                    vehicle_id,
                    name,
                    recorded_date
        """

        self.env.cr.execute(query)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)))
