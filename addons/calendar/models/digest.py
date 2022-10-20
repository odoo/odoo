# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_meetings_booked = fields.Boolean('# Meetings Booked')
    kpi_nbr_of_meetings_booked_value = fields.Integer(compute='_compute_kpi_nbr_of_meetings_booked_value')

    def _compute_kpi_nbr_of_meetings_booked_value(self):
        for record in self:
            start, end, _ = record._get_kpi_compute_parameters()
            record.kpi_nbr_of_meetings_booked_value = self.env['calendar.event'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end)
            ])
