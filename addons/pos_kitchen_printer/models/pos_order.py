# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    multiprint_resume = fields.Char()

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['multiprint_resume'] = ui_order.get('multiprint_resume')
        return order_fields

    def _get_fields_for_draft_order(self):
        fields = super(PosOrder, self)._get_fields_for_draft_order()
        fields.append('multiprint_resume')
        return fields

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.append('mp_dirty')
        return fields


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    mp_dirty = fields.Boolean()
