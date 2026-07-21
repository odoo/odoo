from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command


class FacturaDescuentoWizard(models.TransientModel):
    _name = 'distribuidora.factura.descuento.wizard'
    _description = "Descuento general para facturas de cliente"

    move_id = fields.Many2one(
        'account.move', required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    porcentaje = fields.Float(string="Porcentaje de descuento", required=True)

    @api.constrains('porcentaje')
    def _check_porcentaje(self):
        for wizard in self:
            if not 0 < wizard.porcentaje <= 100:
                raise ValidationError(_(
                    "El porcentaje de descuento debe ser mayor a 0 y menor o igual a 100."
                ))

    def _get_discount_product(self):
        self.ensure_one()
        company = self.move_id.company_id
        discount_product = company.sale_discount_product_id
        if not discount_product:
            discount_product = self.env['product.product'].create({
                'name': _("Descuento"),
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
                'company_id': company.id,
            })
            company.sale_discount_product_id = discount_product
        return discount_product

    def action_aplicar(self):
        self.ensure_one()
        move = self.move_id
        AccountTax = self.env['account.tax']

        product_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        base_lines = [
            AccountTax._prepare_base_line_for_taxes_computation(line) for line in product_lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, move.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, move.company_id)

        def grouping_function(base_line):
            return {'product_id': None}

        discount_base_lines = AccountTax._prepare_global_discount_lines(
            base_lines=base_lines,
            company=move.company_id,
            amount_type='percent',
            amount=self.porcentaje,
            computation_key=f'distribuidora_descuento_general,{self.id}',
            grouping_function=grouping_function,
        )

        discount_product = self._get_discount_product()

        move.invoice_line_ids = [
            Command.create({
                'name': _("Descuento %(percent)s%%", percent=self.porcentaje),
                'product_id': discount_product.id,
                'price_unit': base_line['price_unit'],
                'quantity': base_line['quantity'],
                'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                'extra_tax_data': AccountTax._export_base_line_extra_tax_data(base_line),
                'sequence': 999,
            })
            for base_line in discount_base_lines
        ]
