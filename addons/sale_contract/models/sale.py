from openerp import models, fields, api


class product_template(models.Model):
    """ Add recurrent_invoice field to product template if it is true,
    it will add to related contract.
    """
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        string='Recurrent Invoice Product', default=False,
        help="If selected, this product will be added to the "
        "related contract (which must be associated with the SO). \n"
        "It will be used as product for invoice lines and generate "
        "the recurring invoices automatically")


class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    update_contract = fields.Boolean("Update Contract", help="If set, the associated contract will be overwritten by this sale order (every recurring line of the contract not in this sale order will be deleted).")

    @api.multi
    def action_button_confirm(self):
        for order in self:
            if order.project_id and order.update_contract:
                order.project_id.write({'recurring_invoice_line_ids': [(5, 0, 0)]})
        return super(sale_order, self).action_button_confirm()


class sale_order_line(models.Model):
    _name = "sale.order.line"
    _inherit = "sale.order.line"

    @api.multi
    def button_confirm(self):
        for order_line in self:
            if order_line.product_id.recurring_invoice and order_line.order_id.project_id:
                recurring_line_id = False
                if order_line.product_id in [line.product_id for line in order_line.order_id.project_id.recurring_invoice_line_ids]:
                    for line in order_line.order_id.project_id.recurring_invoice_line_ids:
                        if line.product_id == order_line.product_id and line.uom_id == order_line.product_uom:
                            recurring_line_id = line.id
                            quantity = line.quantity
                            break
                if recurring_line_id:
                    invoice_line_ids = [((1, recurring_line_id, {
                        'quantity': quantity + order_line.product_uom_qty,
                    }))]
                else:
                    invoice_line_ids = [((0, 0, {
                        'product_id': order_line.product_id.id,
                        'analytic_account_id': order_line.order_id.project_id.id,
                        'name': order_line.name,
                        'quantity': order_line.product_uom_qty,
                        'uom_id': order_line.product_uom.id,
                        'price_unit': order_line.price_unit,
                        'discount': order_line.discount if order_line.order_id.update_contract else False,
                    }))]
                analytic_values = {'recurring_invoice_line_ids': invoice_line_ids}
                if not order_line.order_id.project_id.partner_id:
                    analytic_values['partner_id'] = order_line.order_id.partner_id.id
                order_line.order_id.project_id.write(analytic_values)
        return super(sale_order_line, self).button_confirm()