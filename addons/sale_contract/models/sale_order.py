# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
import datetime

from openerp import api, fields, models
from openerp.tools.translate import _


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    def _get_subscription(self):
        for order in self:
            order.subscription_id = self.env['sale.subscription'].search([('analytic_account_id', '=', order.project_id.id)], limit=1)

    update_contract = fields.Boolean("Update Contract", help="If set, the associated contract will be overwritten by this sale order (every recurring line of the contract not in this sale order will be deleted).")
    subscription_id = fields.Many2one('sale.subscription', 'Subscription', compute=_get_subscription)

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.subscription_id:
                # wipe the subscription clean if needed
                if order.update_contract:
                    to_remove = [(2, line.id, 0) for line in order.subscription_id.recurring_invoice_line_ids]
                    order.subscription_id.sudo().write({'recurring_invoice_line_ids': to_remove, 'description': order.note})
                # add new lines or increment quantities on existing lines
                values = {'recurring_invoice_line_ids': []}
                for line in order.order_line:
                    if line.product_id.recurring_invoice:
                        recurring_line_id = False
                        if line.product_id in [subscr_line.product_id for subscr_line in order.subscription_id.recurring_invoice_line_ids]:
                            for subscr_line in order.subscription_id.recurring_invoice_line_ids:
                                if subscr_line.product_id == line.product_id and subscr_line.uom_id == line.product_uom:
                                    recurring_line_id = subscr_line.id
                                    quantity = subscr_line.sold_quantity
                                    break
                        if recurring_line_id:
                            values['recurring_invoice_line_ids'].append((1, recurring_line_id, {
                                'sold_quantity': quantity + line.product_uom_qty,
                            }))
                        else:
                            values['recurring_invoice_line_ids'].append((0, 0, {
                                'product_id': line.product_id.id,
                                'analytic_account_id': order.subscription_id.id,
                                'name': line.name,
                                'sold_quantity': line.product_uom_qty,
                                'uom_id': line.product_uom.id,
                                'price_unit': line.price_unit,
                                'discount': line.discount if line.order_id.update_contract else False,
                            }))
                order.subscription_id.sudo().write(values)
                order.subscription_id.sudo().increment_period()
                order.action_done()
        return res

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.project_id and self.update_contract:
            subscr = self.env['sale.subscription'].search([('analytic_account_id', '=', self.project_id.id)], limit=1)
            next_date = datetime.datetime.strptime(subscr.recurring_next_date, "%Y-%m-%d")
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            invoicing_period = relativedelta(**{periods[subscr.recurring_rule_type]: subscr.recurring_interval})
            previous_date = next_date - invoicing_period

            invoice_vals['comment'] = _("This invoice covers the following period: %s - %s") % (previous_date.date(), (next_date - relativedelta(days=1)).date())

        return invoice_vals
