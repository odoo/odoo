# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def create(self, values):
        if values.get('task_id'):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id.id or values.get('so_line', False)
        values.update(self._get_timesheet_cost(values))
        return super(AccountAnalyticLine, self).create(values)

    @api.multi
    def write(self, values):
        so_lines = self.mapped('so_line')
        if values.get('task_id'):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id.id or values.get('so_line', False)
        for line in self:
            values.update(line._get_timesheet_cost(values))
            super(AccountAnalyticLine, line).write(values)

        # Update delivered quantity on SO lines which are not linked to the analytic lines anymore
        so_lines -= self.mapped('so_line')
        if so_lines:
            so_lines.with_context(force_so_lines=so_lines).sudo()._compute_analytic()
        return True

    def _get_timesheet_cost(self, values):
        values = values if values is not None else {}
        if values.get('project_id') or self.project_id:
            if values.get('amount'):
                return {}
            unit_amount = values.get('unit_amount', 0.0) or self.unit_amount
            user_id = values.get('user_id') or self.user_id.id or self._default_user()
            emp = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
            account = values.get('account_id') and self.env['account.analytic.account'].browse([values['account_id']]) or self.account_id or emp.account_id
            cost = emp and emp.timesheet_cost or 0.0
            uom = account.sudo().company_id.project_time_mode_id
            # Nominal employee cost = 1 * company project UoM (project_time_mode_id)
            return {
                'amount': -unit_amount * cost,
                'product_uom_id': uom.id,
                'account_id': values.get('account_id') or self.account_id.id or emp.account_id.id,
            }
        return {}

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
                result.update(self._get_timesheet_cost(result))

        return super(AccountAnalyticLine, self)._get_sale_order_line(vals=result)
