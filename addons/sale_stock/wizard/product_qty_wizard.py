from odoo import api, models, fields


class StockProductQuantityWizard(models.TransientModel):
    _name = 'sale.order.line.wizard'
    _description = "Stock Information Wizard"

    stock_information = fields.Html('Stock Information', readonly=True)

    @api.model
    def default_get(self, fields):
        result = super(StockProductQuantityWizard, self).default_get(fields)
        model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        product_qty = self.env.context.get('product_qty')
        record = self.env[model].browse(active_id)
        vals = record._check_availability_warning(record.product_id, product_qty)
        result.update({'stock_information':  self.env['ir.qweb'].render('sale_stock.stock_informations', values={'data':  vals['stock_info']})})
        return result
