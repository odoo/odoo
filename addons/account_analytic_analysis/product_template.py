# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class product_template(models.Model):
    """ Add recurrent_invoice field to product template if it is true,
    it will add to related contract.
    """
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(string='Recurrent Invoice Product', default=False, 
                                        help="If selected, this product will be added to the "
                                        "related contract (which must be associated with the SO). \n"
                                        "It will be used as product for invoice lines and generate "
                                        "the recurring invoices automatically")

class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    @api.one
    def button_confirm(self):
        if self.product_id.recurring_invoice and self.order_id.project_id:
            invoice_line_ids = [((0, 0, {'product_id': self.product_id.id,
                'analytic_account_id': self.order_id.project_id.id,
                'name': self.name,
                'quantity': self.product_uom_qty, 
                'uom_id': self.product_uom.id,
                'price_unit': self.price_unit,
                'price_subtotal': self.price_subtotal
            }))]
            analytic_values = {'recurring_invoices': True, 'recurring_invoice_line_ids': invoice_line_ids}
            if not self.order_id.project_id.partner_id:
                analytic_values.update({'partner_id': self.order_id.partner_id.id})
            self.order_id.project_id.write(analytic_values)
        return super(sale_order_line, self).button_confirm()
