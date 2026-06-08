# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_certified_attendees = fields.Boolean('Certified Attendees')
    kpi_nbr_of_certified_attendees_value = fields.Integer(
        compute='_compute_kpi_nbr_of_certified_attendees_value'
    )
    kpi_nbr_of_new_attendees = fields.Boolean('Attendee Registrations')
    kpi_nbr_of_new_attendees_value = fields.Integer(compute='_compute_kpi_nbr_of_new_attendees_value')

    def _compute_kpi_nbr_of_certified_attendees_value(self):
        self._raise_if_not_member_of('website_slides.group_website_slides_manager')
        self._calculate_kpi(
            'slide.channel.partner',
            digest_kpi_field='kpi_nbr_of_certified_attendees_value',
            date_field='completion_date',
            is_cross_company=True)

    def _compute_kpi_nbr_of_new_attendees_value(self):
        self._raise_if_not_member_of('website_slides.group_website_slides_manager')
        self._calculate_kpi(
            'slide.channel.partner', digest_kpi_field='kpi_nbr_of_new_attendees_value', is_cross_company=True)

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('website_slides.website_slides_menu_root').id
        res['kpi_action']['kpi_nbr_of_new_attendees'] = (
            f'website_slides.slide_channel_partner_action_report?menu_id={menu_id}')
        res['kpi_action']['kpi_nbr_of_certified_attendees'] = (
            f'website_slides.slide_channel_partner_action_report_certified?menu_id={menu_id}')
        res['is_cross_company'].update(('kpi_nbr_of_certified_attendees', 'kpi_nbr_of_new_attendees'))
        res['kpi_sequence']['kpi_nbr_of_new_attendees'] = 13500
        res['kpi_sequence']['kpi_nbr_of_certified_attendees'] = 13505
        return res
