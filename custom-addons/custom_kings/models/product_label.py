from odoo import models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_print_custom_labels(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Custom Labels',
            'view_mode': 'form',
            'res_model': 'product.label.wizard',
            'target': 'new',
            'context': {
                'default_label_type': 'barcode',
                'active_id': self.id,
                'active_model': 'product.template',
            },
        }
