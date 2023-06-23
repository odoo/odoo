# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ewaybill_id = fields.Many2one(
    comodel_name='l10n.in.ewaybill',
    string='Ewaybill')

    def action_open_ewaybill_form(self):
        self.ensure_one()

        existing_ewaybill = self.env['l10n.in.ewaybill'].search([('stock_picking_id', '=', self.id)], limit=1)
        context = {
            'default_stock_picking_id': self.id,
            'create': False,
        }

        if existing_ewaybill:
            context.update({
                'default_stock_picking_id': existing_ewaybill.id,
            })

        return {
            'name': "Ewaybill",
            'res_model': 'l10n.in.ewaybill',
            'type': 'ir.actions.act_window',
            'res_id': existing_ewaybill.id if existing_ewaybill else False,
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_in_ewaybill_stock.l10n_in_ewaybill_form_view').id,
            'context': context,
        }

    def action_open_ewaybill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'l10n.in.ewaybill',
            'res_id': self.ewaybill_id.id,
            'target': 'current',
            'context': {'create': False},
        }
