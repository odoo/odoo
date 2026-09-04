# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_eg_building_no = fields.Char('Building No.')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_eg_building_no']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_eg_building_no']

    def _check_l10n_eg_missing_address_data(self):
        """Returns true if the partner has any address data missing"""
        address_values = [self.street, self.city, self.country_id, self.vat]
        return any(not value for value in address_values) or (self.country_code == 'EG' and not self.l10n_eg_building_no)
