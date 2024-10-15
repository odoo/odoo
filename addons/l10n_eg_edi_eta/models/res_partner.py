# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api
from odoo.addons import account


class ResPartner(account.ResPartner):

    l10n_eg_building_no = fields.Char('Building No.')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_eg_building_no']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_eg_building_no']
