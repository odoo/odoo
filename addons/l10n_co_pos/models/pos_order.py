# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _get_create_from_ui_returned_fields_name(self):
        fields_name = super()._get_create_from_ui_returned_fields_name()
        fields_name.append('name')
        return fields_name

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        res['l10n_co_dian'] = order.name
        return res
