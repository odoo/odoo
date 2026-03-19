from odoo import api, models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    @api.model
    def get_receipt_template_for_pos_frontend(self):
        templates = super().get_receipt_template_for_pos_frontend()
        name = 'pos_self_order.pos_qr_receipt'
        templates.append([name, self.env['ir.qweb']._get_template(name)[1]])
        return templates
