# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo import api, fields, models, _
from odoo.fields import Domain
from odoo.tools.misc import unquote

from odoo.addons.sale_project.models.account_analytic_line import BILLABLE_TYPES

TIMESHEET_BILLABLE_TYPES = [
    ('02_billable_fixed', 'Billed at a Fixed price'),
    ('03_timesheet_revenues', 'Revenues Timesheets'),
    ('04_billable_time', 'Billed on Timesheets'),
    ('06_billable_milestones', 'Billed on Milestones'),
    ('08_billable_manual', 'Billed Manually'),
    ('09_non_billable', 'Non-Billable'),
]

BILLABLE_TYPES += TIMESHEET_BILLABLE_TYPES


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _domain_so_line(self):
        domain = super()._domain_so_line()

        return Domain.AND([
            domain,
            self.env['sale.order.line']._sellable_lines_domain(),
            self.env['sale.order.line']._domain_sale_line_service(),
            [
                ('order_partner_id.commercial_partner_id', '=', unquote('commercial_partner_id')),
            ],
        ])

    billable_type = fields.Selection(selection_add=TIMESHEET_BILLABLE_TYPES)
    commercial_partner_id = fields.Many2one('res.partner', compute="_compute_commercial_partner")
    so_line = fields.Many2one(
        falsy_value_label="Non-billable",
        help="Sales order item to which the time spent will be added in order to be invoiced to your customer. Remove the sales order item for the timesheet entry to be non-billable."
    )
    is_so_line_edited = fields.Boolean("Is Sales Order Item Manually Edited")
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    sale_order_state = fields.Selection(related='order_id.state')

    @api.depends('project_id.partner_id.commercial_partner_id', 'task_id.partner_id.commercial_partner_id')
    def _compute_commercial_partner(self):
        for timesheet in self:
            timesheet.commercial_partner_id = timesheet.task_id.sudo().partner_id.commercial_partner_id or timesheet.project_id.sudo().partner_id.commercial_partner_id

    @api.depends('so_line.product_id', 'project_id.billing_type', 'amount')
    def _compute_project_billable_type(self):
        timesheets_with_project = self.filtered(lambda t: t.project_id)
        for timesheet in timesheets_with_project:
            invoice_type = False
            if not timesheet.so_line:
                invoice_type = '09_non_billable' if timesheet.project_id.billing_type != 'manually' else '08_billable_manual'
            elif timesheet.so_line.product_id.type == 'service':
                if timesheet.so_line.product_id.invoice_policy == 'delivery':
                    if timesheet.so_line.product_id.service_type == 'timesheet':
                        invoice_type = '03_timesheet_revenues' if timesheet.amount > 0 and timesheet.unit_amount > 0 else '04_billable_time'
                    else:
                        service_type = timesheet.so_line.product_id.service_type
                        if service_type == 'milestones':
                            invoice_type = '06_billable_milestones'
                        elif service_type == 'manual':
                            invoice_type = '08_billable_manual'
                        else:
                            invoice_type = '02_billable_fixed'
                elif timesheet.so_line.product_id.invoice_policy == 'order':
                    invoice_type = '02_billable_fixed'
            timesheet.billable_type = invoice_type
        super(AccountAnalyticLine, self - timesheets_with_project)._compute_project_billable_type()

    @api.depends('task_id.sale_line_id', 'project_id.sale_line_id', 'employee_id', 'project_id.allow_billable')
    def _compute_so_line(self):
        super()._compute_so_line()
        # Get only the timesheets that are not yet invoiced
        for timesheet in self.filtered(lambda t: t.project_id and not t.is_so_line_edited and t._is_not_billed()):
            timesheet.so_line = timesheet.project_id.allow_billable and timesheet._timesheet_determine_sale_line()

    @api.depends('so_line')
    def _compute_order_id(self):
        super()._compute_order_id()
        # compute only for timesheets
        for timesheet in self.filtered('project_id'):
            timesheet.order_id = timesheet.so_line.order_id

    @api.depends('reinvoice_move_id.state')
    def _compute_partner_id(self):
        super(AccountAnalyticLine, self.filtered(lambda t: t._is_not_billed()))._compute_partner_id()

    @api.depends('reinvoice_move_id.state')
    def _compute_project_id(self):
        super(AccountAnalyticLine, self.filtered(lambda t: t._is_not_billed()))._compute_project_id()

    def _is_readonly(self):
        return super()._is_readonly() or not self._is_not_billed()

    def _is_not_billed(self):
        self.ensure_one()
        return not self.reinvoice_move_id or (self.reinvoice_move_id.state == 'cancel' and self.reinvoice_move_id.payment_state != 'invoicing_legacy')

    def _check_timesheet_can_be_billed(self):
        return self.so_line in self.project_id.mapped('sale_line_employee_ids.sale_line_id') | self.task_id.sale_line_id | self.project_id.sale_line_id

    def _restricted_fields_when_invoiced(self):
        return super()._restricted_fields_when_invoiced() + ['employee_id', 'project_id', 'task_id']

    def _get_invoiced_line_write_error(self):
        if self.project_id:
            return self.env._("You cannot modify timsheets that are already invoiced.")
        return super()._get_invoiced_line_write_error()

    def _get_invoiced_line_delete_error(self):
        if any(timesheet.project_id for timesheet in self):
            return self.env._("You cannot remove timsheets that are already invoiced.")
        return super()._get_invoiced_line_delete_error()

    def _timesheet_determine_sale_line(self):
        """ Deduce the SO line associated to the timesheet line:
            1/ timesheet on task rate: the so line will be the one from the task
            2/ timesheet on employee rate task: find the SO line in the map of the project (even for subtask), or fallback on the SO line of the task, or fallback
                on the one on the project
        """
        self.ensure_one()

        if not self.task_id:
            if self.project_id.pricing_type == 'employee_rate':
                map_entry = self._get_employee_mapping_entry()
                if map_entry:
                    return map_entry.sale_line_id
            if self.project_id.sale_line_id:
                return self.project_id.sale_line_id
        if self.task_id.allow_billable and self.task_id.sale_line_id:
            if self.task_id.pricing_type in ('task_rate', 'fixed_rate'):
                return self.task_id.sale_line_id
            else:  # then pricing_type = 'employee_rate'
                map_entry = self.project_id.sale_line_employee_ids.filtered(
                    lambda map_entry:
                        map_entry.employee_id == (self.employee_id or self.env.user.employee_id)
                        and map_entry.sale_line_id.order_partner_id.commercial_partner_id == self.task_id.partner_id.commercial_partner_id
                )
                if map_entry:
                    return map_entry.sale_line_id
                return self.task_id.sale_line_id
        return False

    def _timesheet_get_portal_domain(self):
        """ Only the timesheets with a product invoiced on delivered quantity are concerned.
            since in ordered quantity, the timesheet quantity is not invoiced,
            thus there is no meaning of showing invoice with ordered quantity.
        """
        domain = super()._timesheet_get_portal_domain()
        return Domain.AND([domain, [('billable_type', 'in', ['04_billable_time', '09_non_billable', '02_billable_fixed', '08_billable_manual', '06_billable_milestones'])]])

    @api.model
    def _timesheet_get_sale_domain(self, order_lines_ids, invoice_ids):
        if not invoice_ids:
            return [('so_line', 'in', order_lines_ids.ids)]

        return [
            '|',
            '&',
            ('reinvoice_move_id', 'in', invoice_ids.ids),
            # TODO : Master: Check if non_billable should be removed ?
            ('billable_type', 'in', ['04_billable_time', '09_non_billable']),
            '&',
            ('billable_type', '=', '02_billable_fixed'),
                '&',
                ('so_line', 'in', order_lines_ids.ids),
                ('reinvoice_move_id', '=', False),
        ]

    def _get_timesheets_to_merge(self):
        res = super()._get_timesheets_to_merge()
        return res.filtered(lambda l: not l.reinvoice_move_id or l.reinvoice_move_id.state != 'posted')

    def _get_employee_mapping_entry(self):
        self.ensure_one()
        return self.env['project.sale.line.employee.map'].search([('project_id', '=', self.project_id.id), ('employee_id', '=', self.employee_id.id or self.env.user.employee_id.id)])

    def _hourly_cost(self):
        if self.project_id.pricing_type == 'employee_rate':
            mapping_entry = self._get_employee_mapping_entry()
            if mapping_entry:
                return mapping_entry.cost
        return super()._hourly_cost()

    def action_sale_order_from_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'views': [[False, 'form']],
            'context': {'create': False, 'show_sale': True},
            'res_id': self.order_id.id,
        }

    def action_invoice_from_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'views': [[False, 'form']],
            'context': {'create': False},
            'res_id': self.reinvoice_move_id.id,
        }

    def _timesheet_convert_sol_uom(self, sol, to_unit):
        to_uom = self.env.ref(to_unit)
        return round(sol.product_uom_id._compute_quantity(sol.product_uom_qty, to_uom, raise_if_failure=False), 2)

    def _is_updatable_timesheet(self):
        return super()._is_updatable_timesheet and self._is_not_billed()

    def _timesheet_preprocess_get_accounts(self, vals):
        so_line = self.env['sale.order.line'].browse(vals.get('so_line'))
        if not (so_line and (distribution := so_line.sudo().analytic_distribution)):
            return super()._timesheet_preprocess_get_accounts(vals)

        company = self.env['res.company'].browse(vals.get('company_id'))
        accounts = self.env['account.analytic.account'].browse([
            int(account_id) for account_id in next(iter(distribution)).split(',')
        ]).exists()

        has_one_project_main_account = len(accounts) == 1 and accounts[0] == self.env['project.project'].sudo().browse(vals.get('project_id')).account_id
        if not accounts or has_one_project_main_account:
            return super()._timesheet_preprocess_get_accounts(vals)

        plan_column_names = {account.root_plan_id._column_name() for account in accounts}
        mandatory_plans = [plan for plan in self._get_mandatory_plans(company, business_domain='timesheet') if plan['column_name'] != 'account_id']
        missing_plan_names = [plan['name'] for plan in mandatory_plans if plan['column_name'] not in plan_column_names]
        if missing_plan_names:
            raise ValidationError(_(
                "'%(missing_plan_names)s' analytic plan(s) required on the analytic distribution of the sale order item '%(so_line_name)s' linked to the timesheet.",
                missing_plan_names=missing_plan_names,
                so_line_name=so_line.name,
            ))

        account_id_per_fname = dict.fromkeys(self._get_plan_fnames(), False)
        for account in accounts:
            account_id_per_fname[account.root_plan_id._column_name()] = account.id
        return account_id_per_fname

    def _timesheet_postprocess(self, values):
        if values.get('so_line'):
            for timesheet in self.sudo():
                # If no account_id was found in the SOL's distribution, we fallback on the project's account_id
                if not timesheet.account_id:
                    timesheet.account_id = timesheet.project_id.account_id
        return super()._timesheet_postprocess(values)
