# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['mail.thread.phone', 'res.partner']

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self._phone_format(fname='phone', force_format='INTERNATIONAL') or self.phone

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self._phone_format(fname='mobile', force_format='INTERNATIONAL') or self.mobile

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        partners.mapped(lambda partner: partner._format_phone_numbers())
        return partners

    def _format_phone_numbers(self):
        """
         Format the mobile and phone numbers of the record to international format.

         This method is used to ensure consistent phone number formatting across the system.
         It's particularly useful in modules like `website_sale`, where properly formatted

         The method attempts to format both mobile and phone numbers if they exist.
         If formatting fails, it falls back to the original number.

         Returns:
         None. The method updates the mobile and phone fields in place.
         """
        if self.mobile:
            self.mobile = self._phone_format(fname='mobile', country=self.country_id, force_format='INTERNATIONAL') or self.mobile
        if self.phone:
            self.phone = self._phone_format(fname='phone', country=self.country_id, force_format='INTERNATIONAL') or self.phone
