# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_sale_order_line(self, vals=None):
        result = dict(vals or {})
        if self.project_id:
            if result.get('so_line'):
                sol = self.env['sale.order.line'].browse([result['so_line']])
            else:
                sol = self.so_line
            if not sol:
                sol = self.env['sale.order.line'].search([
                    ('order_id.project_id', '=', self.account_id.id),
                    ('state', '=', 'sale'),
                    ('product_id.track_service', '=', 'timesheet'),
                    ('product_id.type', '=', 'service')],
                    limit=1)
            if sol:
                result.update({
                    'so_line': sol.id,
                    'product_id': sol.product_id.id,
                })
                result = self._get_timesheet_cost(result)

        result = super(AccountAnalyticLine, self)._get_sale_order_line(vals=result)
        return result

    def _get_timesheet_cost(self, vals=None):
        result = dict(vals or {})
        if result.get('project_id') or self.project_id:
            if result.get('amount'):
                return result
            unit_amount = result.get('unit_amount', 0.0) or self.unit_amount
            user_id = result.get('user_id') or self.user_id.id or self._default_user()
            user = self.env['res.users'].browse([user_id])
            emp = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
            cost = emp and emp.timesheet_cost or 0.0
            uom = (emp or user).company_id.project_time_mode_id
            # Nominal employee cost = 1 * company project UoM (project_time_mode_id)
            result.update(
                amount=(-unit_amount * cost),
                product_uom_id=uom.id
            )
        return result

    @api.model
    def _update_values(self, values):
        if values.get('task_id', False):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id and task.sale_line_id.id or values.get('so_line', False)

    @api.multi
    def write(self, values):
        self._update_values(values)
        for line in self:
            values = line._get_timesheet_cost(vals=values)
            super(AccountAnalyticLine, line).write(values)
        return True

    @api.model
    def create(self, values):
        self._update_values(values)
        values = self._get_timesheet_cost(vals=values)
        return super(AccountAnalyticLine, self).create(values)
