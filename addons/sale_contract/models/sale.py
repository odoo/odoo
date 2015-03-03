# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
import datetime

from openerp import models, fields, api
from openerp.tools.translate import _


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
                to_remove = [(2, line.id, 0) for line in order.project_id.recurring_invoice_line_ids]
                order.project_id.sudo().write({'recurring_invoice_line_ids': to_remove, 'description': order.note})
                order.project_id.sudo().increment_period()
        return super(sale_order, self).action_button_confirm()

    @api.model
    def _prepare_invoice(self, order, lines):
        invoice_vals = super(sale_order, self)._prepare_invoice(order, lines)
        if order.project_id and order.update_contract:
            next_date = datetime.datetime.strptime(order.project_id.recurring_next_date, "%Y-%m-%d")
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[order.project_id.recurring_rule_type]: order.project_id.recurring_interval})
            previous_date = next_date - invoicing_period

            invoice_vals['comment'] = _("This invoice covers the following period: %s - %s") % (previous_date.date(), (next_date - relativedelta(days=1)).date())

        return invoice_vals


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
                            quantity = line.sold_quantity
                            break
                if recurring_line_id:
                    invoice_line_ids = [((1, recurring_line_id, {
                        'sold_quantity': quantity + order_line.product_uom_qty,
                    }))]
                else:
                    invoice_line_ids = [((0, 0, {
                        'product_id': order_line.product_id.id,
                        'analytic_account_id': order_line.order_id.project_id.id,
                        'name': order_line.name,
                        'sold_quantity': order_line.product_uom_qty,
                        'uom_id': order_line.product_uom.id,
                        'price_unit': order_line.price_unit,
                        'discount': order_line.discount if order_line.order_id.update_contract else False,
                    }))]
                analytic_values = {'recurring_invoice_line_ids': invoice_line_ids}
                if not order_line.order_id.project_id.partner_id:
                    analytic_values['partner_id'] = order_line.order_id.partner_id.id
                order_line.order_id.project_id.sudo().write(analytic_values)
        return super(sale_order_line, self).button_confirm()