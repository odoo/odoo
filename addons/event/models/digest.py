# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_registrations = fields.Boolean('# Registrations')
    kpi_nbr_of_registrations_value = fields.Integer(compute='_compute_kpi_nbr_of_registrations_value')

    def _compute_kpi_nbr_of_registrations_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            record.kpi_nbr_of_registrations_value = self.env['event.registration'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end),
                ('company_id', '=', company.id)
            ])

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_nbr_of_registrations'] = 'event.action_registration'
        return res
