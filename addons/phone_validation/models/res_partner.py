# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.phone_validation.tools import phone_validation


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self._phone_format(fname='phone', force_format='INTERNATIONAL') or self.phone

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self._phone_format(fname='mobile', force_format='INTERNATIONAL') or self.mobile

    def _phone_format_fields(self):
        return ('phone', 'mobile')

    def _phone_format_values(self, vals, country=False):
        for fname in self._phone_format_fields():
            number = vals.get(fname)
            if not number:
                continue
            formatted = self._phone_format_number(
                str(number),
                country=country or self.env.company.country_id,
                force_format='INTERNATIONAL',
            )
            if formatted:
                vals[fname] = formatted

    @api.model_create_multi
    def create(self, vals_list):
        Country = self.env['res.country']
        for vals in vals_list:
            country = Country.browse(vals['country_id']) if vals.get('country_id') else False
            self._phone_format_values(vals, country=country)
        return super().create(vals_list)

    def write(self, vals):
        if any(fname in vals for fname in self._phone_format_fields()):
            country = False
            if vals.get('country_id'):
                country = self.env['res.country'].browse(vals['country_id'])
            elif len(self) == 1:
                country = self.country_id
            self._phone_format_values(vals, country=country)
        return super().write(vals)
