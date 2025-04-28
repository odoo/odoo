from odoo import models, fields
from odoo.exceptions import UserError
from logging import Logger

_logger = Logger(__name__)

class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Label Print Wizard'

    label_type = fields.Selection([
        ('barcode', 'Barcode Label'),
        ('product', 'Product Details Label')
    ], string="Label Type", required=True, default='barcode')

    custom_quantity = fields.Integer('Quantity', default=1, required=True)


    def action_print_labels(self):
        """Generates the correct report based on selection"""
        self.ensure_one()

        report_id = 'custom_kings.action_report_product_barcode' if self.label_type == 'barcode' else 'custom_kings.action_report_product_details'

        _logger.info(f"🖨️ Printing Label: {self.label_type}, Using Report ID: {report_id}")

        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')

        if not active_model or not active_id:
            raise UserError("No product selected for label printing.")

        product = self.env[active_model].browse(active_id)

        return self.env.ref(report_id).report_action(
            product,
            data={
                'custom_quantity': self.custom_quantity,
                'product_name': product.name,
                'default_code': product.default_code,
                'list_price': product.list_price,
                'currency_symbol': product.currency_id.symbol,
                'barcode': product.barcode,
                'description': product.description_sale or product.description
            },
            config=False,
        )
