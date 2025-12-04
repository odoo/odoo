# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_registrations = fields.Boolean('Registrations')
    kpi_nbr_of_registrations_value = fields.Integer(compute='_compute_kpi_nbr_of_registrations_value')

    def _compute_kpi_nbr_of_registrations_value(self):
        self._raise_if_not_member_of('event.group_event_manager')
        self._calculate_kpi(
            'event.registration',
            digest_kpi_field='kpi_nbr_of_registrations_value')

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        res['kpi_action']['kpi_nbr_of_registrations'] = 'event.action_registration'
        res['kpi_sequence']['kpi_nbr_of_registrations'] = 10500
        return res
