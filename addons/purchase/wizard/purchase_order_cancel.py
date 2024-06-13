from odoo import models, fields


class PurchaseCancelWizard(models.TransientModel):
    _name = 'purchase.cancel.wizard'
    _description = 'Wizard to confirm purchase order cancellation'

    def default_get(self, fields):
        defaults = super().default_get(fields)
        defaults['purchase_count'] = len(self._context.get('default_purchase_order_ids', []))
        return defaults

    purchase_order_ids = fields.Many2many('purchase.order', string="Purchase Orders")
    purchase_count = fields.Integer(readonly=True)

    def action_confirm(self):
        self.purchase_order_ids.button_cancel()
        return {'type': 'ir.actions.act_window_close'}

    def action_discard(self):
        return {'type': 'ir.actions.act_window_close'}
