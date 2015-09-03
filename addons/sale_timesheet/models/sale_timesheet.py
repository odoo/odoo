# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields
from openerp.tools.translate import _

from openerp.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_uom_hours(self):
        try:
            return self.env.ref("product.product_uom_hour")
        except ValueError:
            return False
    project_time_mode_id = fields.Many2one('product.uom', string='Timesheet UoM', default=_get_uom_hours)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    timesheet_cost = fields.Float(string='Timesheet Cost', default=0.0)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    track_service = fields.Selection(selection_add=[('timesheet', 'Timesheets on contract')])

    @api.onchange('type', 'invoice_policy')
    def onchange_type_timesheet(self):
        if self.type == 'service' and self.invoice_policy == 'cost':
            self.track_service = 'timesheet'
        if self.type != 'service':
            self.track_service = 'manual'
        return {}


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_sale_order_line(self, vals=None):
        result = dict(vals or {})
        if self.is_timesheet:
            sol = result.get('so_line', False) or self.so_line
            if not sol and self.account_id:
                sol = self.env['sale.order.line'].search([
                    ('order_id.project_id', '=', self.account_id.id),
                    ('state', '=', 'sale'),
                    ('product_id.track_service', '=', 'timesheet'),
                    ('product_id.type', '=', 'service')],
                    limit=1)
            else:
                sol = self.so_line
            if sol:
                emp = self.env['hr.employee'].search([('user_id', '=', self.user_id.id)], limit=1)
                if result.get('amount', False):
                    amount = result['amount']
                elif emp and emp.timesheet_cost:
                    amount = -self.unit_amount * emp.timesheet_cost
                elif self.product_id and self.product_id.standard_price:
                    amount = -self.unit_amount * self.product_id.standard_price
                else:
                    amount = self.amount or 0.0
                result.update({
                    'product_id': sol.product_id.id,
                    'product_uom_id': self.env.user.company_id.project_time_mode_id.id or sol.product_id.uom_id.id,
                    'amount': amount,
                    'so_line': sol.id,
                })
        result = super(AccountAnalyticLine, self)._get_sale_order_line(vals=result)
        return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.one
    @api.constrains('order_line')
    def _check_multi_timesheet(self):
        count = 0
        for line in self.order_line:
            if line.product_id.track_service == 'timesheet':
                count += 1
            if count > 1:
                raise UserError(_("You can use only one product on timesheet within the same sale order. You should split your order to include only one contract based on time and material."))
        return {}

    @api.one
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        if not self.project_id:
            for line in self.order_line:
                if line.product_id.track_service == 'timesheet':
                    self._create_analytic_account(prefix=self.product_id.default_code or None)
                    break
        return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic(self, domain=None):
        if not domain:
            domain = [('so_line', 'in', self.ids), '|', ('amount', '<', 0.0), ('is_timesheet', '=', True)]
        return super(SaleOrderLine, self)._compute_analytic(domain=domain)
