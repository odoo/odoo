from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TiktokShippingLabelPDF(models.TransientModel):
    _name = 'tiktok.shipping.label.pdf'
    _description = "Tiktok Shipping Label PDF"

    name = fields.Char('Name')
    pdf_file = fields.Binary('Click On Download Link To Download PDF', readonly=True)

    def action_back(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'tiktok.shipping.label',
            'target': 'new'
        }
