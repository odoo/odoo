# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields

class Company(models.Model):
    _inherit = 'res.company'

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    is_timesheet = fields.Boolean(string="Is a Timesheet")

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'

    use_timesheets = fields.Boolean('Timesheets', help="Check this field if this project manages timesheets", deprecated=True)
    invoice_on_timesheets = fields.Boolean('Timesheets', help="Check this field if this project manages timesheets")
    total_cost_revenue = fields.Float(compute='_compute_total_cost_revenue', string="Cost/Revenue")

    @api.multi
    def _compute_total_cost_revenue(self):
        line_data = self.env['account.analytic.line'].read_group([('account_id', 'in', self.ids)], ['amount', 'account_id'], ['account_id'])
        mapped_data = dict([(m['account_id'][0], m['amount']) for m in line_data])
        for analytic_account in self:
            analytic_account.total_cost_revenue = mapped_data.get(analytic_account.id, 0.0)

    @api.onchange('invoice_on_timesheets')
    def onchange_invoice_on_timesheets(self):
        result = {'value': {}}
        if not self.invoice_on_timesheets:
            return {'value': {'to_invoice': False}}
        try:
            to_invoice = self.env['ir.model.data'].xmlid_to_res_id('hr_timesheet_invoice.timesheet_invoice_factor1')
            result['value']['to_invoice'] = to_invoice
        except ValueError:
            pass
        return result

    @api.onchange('template_id')
    def V8_on_change_template(self):
        new_values = self.on_change_template(selftemplate_id.id, self.date_start)
        if new_values.get("value"):
            for key, value in new_values["value"].iteritems():
                setattr(self, key, value)

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['invoice_on_timesheets'] = template.invoice_on_timesheets
        return res
