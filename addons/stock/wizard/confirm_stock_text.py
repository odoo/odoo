from odoo import fields, models


class ConfirmStockText(models.TransientModel):
    _name = 'confirm.stock.text'
    _description = 'Confirm Stock Text'

    pick_ids = fields.Many2many('stock.picking', 'stock_picking_text_rel')
    company_id = fields.Many2one('res.company',
        string='Company', required=True,
        default=lambda self: self.env.company,
    )
    confirmation_type = fields.Selection(related='company_id.confirmation_type', readonly=False)

    def send_text(self):
        self.ensure_one()
        for company in self.pick_ids.company_id:
            company.sudo().write({'has_received_text_warning': True})
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        return pickings_to_validate.button_validate()

    def dont_send_text(self):
        self.ensure_one()
        for company in self.pick_ids.company_id:
            company.sudo().write({
                'has_received_text_warning': True,
                'text_confirmation': False,
            })
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        return pickings_to_validate.button_validate()
