# -*- coding: utf-8 -*-

from openerp import models, fields, api
from dateutil.relativedelta import relativedelta
import datetime


class sale_quote_template(models.Model):
    _name = "sale.quote.template"
    _inherit = "sale.quote.template"

    contract_template = fields.Many2one('account.analytic.account', 'Contract Template')

    @api.onchange('contract_template')
    def onchange_contract_template(self):
        quote_lines = [(0, 0, {
            'product_id': mand_line.product_id.id,
            'uom_id': mand_line.uom_id.id,
            'name': mand_line.name,
            'product_uom_qty': mand_line.quantity,
            'product_uom_id': mand_line.uom_id.id,
            'price_unit': mand_line.price_unit,
            }) for mand_line in self.contract_template.recurring_invoice_line_ids]
        options = [(0, 0, {
            'product_id': opt_line.product_id.id,
            'uom_id': opt_line.uom_id.id,
            'name': opt_line.name,
            'product_uom_qty': opt_line.quantity,
            'price_unit': opt_line.price_unit,
            }) for opt_line in self.contract_template.option_invoice_line_ids]
        self.quote_line = quote_lines
        self.options = options