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
    # FIXME: this field should be in module hr_timesheet, not sale_timesheet
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
            if result.get('so_line'):
                sol = self.env['sale.order.line'].browse([result['so_line']])
            else:
                sol = self.so_line
            if not sol and self.account_id:
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
        if result.get('is_timesheet') or self.is_timesheet:
            if result.get('amount'):
                return result
            unit_amount = result.get('unit_amount', 0.0) or self.unit_amount
            user_id = result.get('user_id') or self.user_id.id
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

    @api.multi
    def write(self, values):
        values = self._get_timesheet_cost(vals=values)
        return super(AccountAnalyticLine, self).write(values)

    @api.model
    def create(self, values):
        values = self._get_timesheet_cost(vals=values)
        return super(AccountAnalyticLine, self).create(values)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids')

    @api.multi
    @api.depends('project_id.line_ids')
    def _compute_timesheet_ids(self):
        for order in self:
            order.timesheet_ids = self.env['account.analytic.line'].search([('is_timesheet', '=', True), ('account_id', '=', order.project_id.id)]) if order.project_id else []
            order.timesheet_count = round(sum([line.unit_amount for line in order.timesheet_ids]), 2)

    @api.multi
    @api.constrains('order_line')
    def _check_multi_timesheet(self):
        for order in self:
            count = 0
            for line in order.order_line:
                if line.product_id.track_service == 'timesheet':
                    count += 1
                if count > 1:
                    raise UserError(_("You can use only one product on timesheet within the same sale order. You should split your order to include only one contract based on time and material."))
        return {}

    @api.multi
    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.project_id:
                for line in order.order_line:
                    if line.product_id.track_service == 'timesheet':
                        order._create_analytic_account(prefix=order.product_id.default_code or None)
                        break
        return result

    @api.multi
    def action_view_timesheet(self):
        self.ensure_one()
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('hr_timesheet.act_hr_timesheet_line_evry1_all_form')
        list_view_id = imd.xmlid_to_res_id('hr_timesheet.hr_timesheet_line_tree')
        form_view_id = imd.xmlid_to_res_id('hr_timesheet.hr_timesheet_line_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if self.timesheet_count > 0:
            result['domain'] = "[('id','in',%s)]" % self.timesheet_ids.ids
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic(self, domain=None):
        if not domain:
            # To filter on analyic lines linked to an expense
            domain = [('so_line', 'in', self.ids), '|', ('amount', '<=', 0.0), ('is_timesheet', '=', True)]
        return super(SaleOrderLine, self)._compute_analytic(domain=domain)

    @api.model
    def _get_analytic_track_service(self):
        return super(SaleOrderLine, self)._get_analytic_track_service() + ['timesheet']
