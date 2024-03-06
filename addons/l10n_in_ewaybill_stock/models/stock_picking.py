# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ewaybill_id = fields.Many2one('l10n.in.ewaybill', string='Ewaybill', compute='_compute_ewaybill_id')

    def _compute_ewaybill_id(self):
        for picking in self:
            picking.ewaybill_id = self.env['l10n.in.ewaybill'].search([('stock_picking_id', '=', picking.id)], limit=1)

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref('l10n_in_ewaybill_stock.l10n_in_ewaybill_form_action').read()[0]

    def action_l10n_in_ewaybill_create(self):
        self.ensure_one()
        if self.ewaybill_id:
            raise UserError(_("Ewaybill already created for this picking."))
        action = self._get_l10n_in_ewaybill_form_action()
        action['context'] = {'default_stock_picking_id': self.id}
        return action

    def action_open_l10n_in_ewaybill(self):
        self.ensure_one()
        action = self._get_l10n_in_ewaybill_form_action()
        action['res_id'] = self.ewaybill_id.id
        return action
