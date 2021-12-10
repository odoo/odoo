# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_registrations = fields.Boolean('Registrations')
    kpi_nbr_of_registrations_value = fields.Integer(compute='_compute_kpi_nbr_of_registrations_value')

    def _compute_kpi_nbr_of_registrations_value(self):
        self._ensure_user_has_one_of_the_group('event.group_event_manager')
        self._calculate_company_based_kpi(
            'event.registration',
            digest_kpi_field='kpi_nbr_of_registrations_value')

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        res['kpi_nbr_of_registrations'] = 'event.action_registration'
        return res
