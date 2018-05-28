# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _default_sale_line_domain(self):
        domain = super(AccountAnalyticLine, self)._default_sale_line_domain()
        return expression.OR([domain, [('qty_delivered_method', '=', 'timesheet')]])

    timesheet_invoice_type = fields.Selection([
        ('billable_time', 'Billable Time'),
        ('billable_fixed', 'Billable Fixed'),
        ('non_billable', 'Non Billable'),
        ('non_billable_project', 'No task found')], string="Billable Type", readonly=True, copy=False)
    timesheet_invoice_id = fields.Many2one('account.invoice', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet")
    timesheet_revenue = fields.Monetary("Revenue", default=0.0, readonly=True, copy=False)

    @api.multi
    def write(self, values):
        # prevent to update invoiced timesheets if one line is of type delivery
        if self.sudo().filtered(lambda aal: aal.so_line.product_id.invoice_policy == "delivery") and self.filtered(lambda timesheet: timesheet.timesheet_invoice_id):
            if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'task_id', 'timesheet_revenue', 'so_line', 'amount', 'date']]):
                raise UserError(_('You can not modify already invoiced timesheets (linked to a Sales order items invoiced on Time and material).'))
        result = super(AccountAnalyticLine, self).write(values)
        return result

    @api.model
    def _timesheet_preprocess(self, values):
        values = super(AccountAnalyticLine, self)._timesheet_preprocess(values)
        # task implies so line
        if 'task_id' in values:
            task = self.env['project.task'].sudo().browse(values['task_id'])
            values['so_line'] = task.sale_line_id.id or values.get('so_line', False)

        # Set product_uom_id now so delivered qty is computed in SO line
        if not 'product_uom_id' in values and all([v in values for v in ['employee_id', 'project_id']]):
            employee = self.env['hr.employee'].sudo().browse(values['employee_id'])
            values['product_uom_id'] = employee.company_id.project_time_mode_id.id
        return values

    @api.multi
    def _timesheet_postprocess_values(self, values):
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        result = super(AccountAnalyticLine, self)._timesheet_postprocess_values(values)
        # (re)compute the UoM from the employee company
        if any([field_name in values for field_name in ['employee_id']]):
            for timesheet in sudo_self:
                uom = timesheet.employee_id.company_id.project_time_mode_id
                result[timesheet.id].update({
                    'product_uom_id': uom.id,
                })
        # (re)compute the theorical revenue
        if any([field_name in values for field_name in ['so_line', 'unit_amount', 'account_id']]):
            for timesheet in sudo_self:
                values_to_write = timesheet._timesheet_compute_theorical_revenue_values()
                if values_to_write:
                    result[timesheet.id].update(values_to_write)
        return result

    @api.multi
    def _timesheet_compute_theorical_revenue_values(self):
        """ This method set the theorical revenue on the current timesheet lines.

            If invoice on delivered quantity:
                timesheet hours * (SO Line Price) * (1- discount),
            elif invoice on ordered quantities & create task:
                min (
                    timesheet hours * (SO Line unit price) * (1- discount),
                    TOTAL SO - TOTAL INVOICED - sum(timesheet revenues with invoice_id=False)
                )
            else:
                0

            :return: a dictionary mapping each record id to its corresponding
                dictionnary values to write (may be empty).
        """
        self.ensure_one()
        timesheet = self

        # find the timesheet UoM
        timesheet_uom = timesheet.product_uom_id
        if not timesheet_uom:  # fallback on default company timesheet UoM
            timesheet_uom = self.env.user.company_id.project_time_mode_id

        # default values
        unit_amount = timesheet.unit_amount
        so_line = timesheet.so_line
        values = {
            'timesheet_revenue': 0.0,
            'timesheet_invoice_type': 'non_billable_project' if not timesheet.task_id else 'non_billable',
        }
        # set the revenue and billable type according to the product and the SO line
        if timesheet.task_id and so_line.product_id.type == 'service':
            # find the analytic account to convert revenue into its currency
            analytic_account = timesheet.account_id
            # convert the unit of mesure into hours
            sale_price_hour = so_line.product_uom._compute_price(so_line.price_unit, timesheet_uom)
            sale_price = so_line.currency_id._convert(
                sale_price_hour, analytic_account.currency_id, so_line.company_id, fields.Date.today())  # amount from SO should be convert into analytic account currency

            # calculate the revenue on the timesheet
            if so_line.product_id.invoice_policy == 'delivery':
                values['timesheet_revenue'] = analytic_account.currency_id.round(unit_amount * sale_price * (1-(so_line.discount/100)))
                values['timesheet_invoice_type'] = 'billable_time' if so_line.product_id.service_type == 'timesheet' else 'billable_fixed'
            elif so_line.product_id.invoice_policy == 'order' and so_line.product_id.service_type == 'timesheet':
                quantity_hour = unit_amount
                if so_line.product_uom.category_id == timesheet_uom.category_id:
                    quantity_hour = so_line.product_uom._compute_quantity(so_line.product_uom_qty, timesheet_uom)
                # compute the total revenue the SO since we are in fixed price
                total_revenue_so = analytic_account.currency_id.round(quantity_hour * sale_price * (1-(so_line.discount/100)))
                # compute the total revenue already existing (without the current timesheet line)
                domain = [('so_line', '=', so_line.id)]
                if timesheet.ids:
                    domain += [('id', 'not in', timesheet.ids)]
                analytic_lines = timesheet.search(domain)
                total_revenue_invoiced = sum(analytic_lines.mapped('timesheet_revenue'))
                # compute (new) revenue of current timesheet line
                values['timesheet_revenue'] = min(
                    analytic_account.currency_id.round(unit_amount * so_line.currency_id._convert(
                        so_line.price_unit, analytic_account.currency_id, so_line.company_id, fields.Date.today()) * (1-so_line.discount)),
                    total_revenue_so - total_revenue_invoiced
                )
                values['timesheet_invoice_type'] = 'billable_fixed'
                # if the so line is already invoiced, and the delivered qty is still smaller than the ordered, then link the timesheet to the invoice
                if so_line.invoice_status == 'invoiced':
                    values['timesheet_invoice_id'] = so_line.invoice_lines and so_line.invoice_lines[0].invoice_id.id
            elif so_line.product_id.invoice_policy == 'order' and so_line.product_id.service_type != 'timesheet':
                values['timesheet_invoice_type'] = 'billable_fixed'

        return values
