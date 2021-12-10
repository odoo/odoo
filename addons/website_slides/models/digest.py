# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_nbr_of_certified_attendees = fields.Boolean('Certified Attendees')
    kpi_nbr_of_certified_attendees_value = fields.Integer(
        compute='_compute_kpi_nbr_of_certified_attendees_value'
    )
    kpi_nbr_of_new_attendees = fields.Boolean('New Attendees')
    kpi_nbr_of_new_attendees_value = fields.Integer(compute='_compute_kpi_nbr_of_new_attendees_value')

    def _compute_kpi_nbr_of_certified_attendees_value(self):
        self._ensure_user_has_one_of_the_group('website_slides.group_website_slides_manager')
        self._calculate_cross_company_kpi(
            'slide.channel.partner',
            digest_kpi_field='kpi_nbr_of_certified_attendees_value',
            date_field='completion_date')

    def _compute_kpi_nbr_of_new_attendees_value(self):
        self._ensure_user_has_one_of_the_group('website_slides.group_website_slides_manager')
        self._calculate_cross_company_kpi('slide.channel.partner', digest_kpi_field='kpi_nbr_of_new_attendees_value')

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        menu_root_id = self.env.ref('website_slides.website_slides_menu_root').id
        res['kpi_nbr_of_new_attendees'] = f'website_slides.slide_channel_partner_action_report&menu_id={menu_root_id}'
        res['kpi_nbr_of_certified_attendees'] = \
            f'website_slides.slide_channel_partner_action_report_certified&menu_id={menu_root_id}'
        return res
