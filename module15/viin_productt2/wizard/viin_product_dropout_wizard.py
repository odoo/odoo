from odoo import fields, models

class ViinProductDropoutWizard(models.TransientModel):
    _name = 'viin.product.dropout.wizard'
    _description = 'Viin Product Dropout Wizard'

    def _default_product(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        return self.env[active_model].browse(active_id)

    product_id = fields.Many2one('viin.product', string='Product', default=_default_product, required=True)
    dropout_reason = fields.Text(string='Dropout Reason', required=True)

    def action_confirm(self):
        self.product_id.dropout_reason = self.dropout_reason
        self.product_id.sold_out = True
