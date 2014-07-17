# -*- coding: utf-8 -*-

from openerp import models, api
from openerp.addons.analytic.models import analytic
from openerp.exceptions import RedirectWarning
from openerp.tools.translate import _


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    @api.one
    def button_confirm(self):
        if self.product_id.recurring_invoice and self.order_id.project_id:
            invoice_line_ids = [((0, 0, {
                'product_id': self.product_id.id,
                'analytic_account_id': self.order_id.project_id.id,
                'name': self.name,
                'quantity': self.product_uom_qty,
                'uom_id': self.product_uom.id,
                'price_unit': self.price_unit,
                'price_subtotal': self.price_subtotal
            }))]
            analytic_values = {'recurring_invoices': True, 'recurring_invoice_line_ids': invoice_line_ids}
            if not self.order_id.project_id.partner_id:
                analytic_values['partner_id'] = self.order_id.partner_id.id
            self.order_id.project_id.write(analytic_values)
        return super(sale_order_line, self).button_confirm()


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.model
    def _check_order_before_confirm(self, order):
        contract_state = dict(analytic.ANALYTIC_ACCOUNT_STATE)
        if order.project_id and order.project_id.state in ['close', 'cancelled', 'pending']:
            action = self.env.ref('analytic.action_account_analytic_account_form').read(
                ['name', 'type', 'view_type', 'view_mode', 'res_model', 'views', 'view_id', 'domain'])[0]
            form_view = self.env.ref('analytic.view_account_analytic_account_form').id

            action['name'] = _('Contract')
            action['domain'] = [('id', '=', order.project_id.id)]
            action['views'] = [(form_view or False, 'form'), (False, 'tree')]
            action['res_id'] = order.project_id.id
            msg = _('''The "%s" contract is in "%s" state, please renew it before confirming the quotation.\n''') % (order.project_id.complete_name, contract_state[order.project_id.state])
            raise RedirectWarning(msg, action, _('Modify Contract'))
        return super(sale_order, self)._check_order_before_confirm(order)
