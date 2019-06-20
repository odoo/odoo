# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _create_account_move(self):
        move = super(PosOrder, self)._create_account_move()
        move['l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return move

    def _prepare_invoice(self):
        inv_vals = super(PosOrder, self)._prepare_invoice()
        inv_vals['l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return inv_vals

    @api.model
    def _order_fields(self, ui_order):
        res = super()._order_fields(ui_order)
        res['l10n_in_unit_id'] = self.env['pos.session'].browse(res['session_id']).config_id.l10n_in_unit_id.id
        return res

    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict", readonly=True)

    @api.model
    def _get_account_move_line_group_data_type_key(self, data_type, values, options={}):
        res = super(PosOrder, self)._get_account_move_line_group_data_type_key(data_type, values, options)
        if data_type == 'tax' and res:
            if self.env['account.tax'].browse(values['tax_line_id']).company_id.country_id.code == 'IN':
                return res + (values['product_uom_id'], values['product_id'])
        return res

    def _prepare_account_move_line(self, line, partner_id, current_company, currency_id, rounding_method):
        res = super(PosOrder, self)._prepare_account_move_line(line, partner_id, current_company, currency_id, rounding_method)
        for line_values in res:
            if line_values.get('data_type') in ['tax','product']:
                line_values['values'].update({
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id
                    })
        return res
