from odoo import models, fields, api


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    pick_to_backorder_ids = fields.Many2many('stock.picking', help='Picking to backorder')

    @api.multi
    def process(self):
        backorder_wizard_dict = super(StockImmediateTransfer, self).process()
        # If the immediate transfer wizard process all our picking but with some back order maybe needed we want to add the backorder already passed to the wizard.
        if backorder_wizard_dict:
            backorder_wizard = self.env['stock.backorder.confirmation'].browse(backorder_wizard_dict.get('res_id', False))
            backorder_wizard.write({'pick_ids': [(4, p.id) for p in self.pick_to_backorder_ids]})
            return backorder_wizard_dict
        # If there is no backorder returned by the immediate transfer basic function we still wanted to process those manually given
        elif self.pick_to_backorder_ids:
            return self.pick_to_backorder_ids.action_generate_backorder_wizard()
        return False
