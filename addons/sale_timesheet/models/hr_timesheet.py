# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import format_list
from odoo.tools.misc import unquote

TIMESHEET_INVOICE_TYPES = [
    ('billable_time', 'Billed on Timesheets'),
    ('billable_fixed', 'Billed at a Fixed price'),
    ('billable_milestones', 'Billed on Milestones'),
    ('billable_manual', 'Billed Manually'),
    ('non_billable', 'Non-Billable'),
    ('timesheet_revenues', 'Timesheet Revenues'),
    ('service_revenues', 'Service Revenues'),
    ('other_revenues', 'Other revenues'),
    ('other_costs', 'Other costs'),
]


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _domain_so_line(self):
        domain = expression.AND([
            self.env['sale.order.line']._sellable_lines_domain(),
            self.env['sale.order.line']._domain_sale_line_service(),
            [
                ('qty_delivered_method', 'in', ['analytic', 'timesheet']),
                ('order_partner_id.commercial_partner_id', '=', unquote('commercial_partner_id')),
            ],
        ])
        return str(domain)

    timesheet_invoice_type = fields.Selection(TIMESHEET_INVOICE_TYPES, string="Billable Type",
            compute='_compute_timesheet_invoice_type', compute_sudo=True, store=True, readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', compute="_compute_commercial_partner")
    timesheet_invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True, copy=False, help="Invoice created from the timesheet", index='btree_not_null')
    so_line = fields.Many2one(compute="_compute_so_line", store=True, readonly=False,
        domain=_domain_so_line,
        help="Sales order item to which the time spent will be added in order to be invoiced to your customer. Remove the sales order item for the timesheet entry to be non-billable.")
    # we needed to store it only in order to be able to groupby in the portal
    order_id = fields.Many2one(related='so_line.order_id', store=True, readonly=True, index=True)
    is_so_line_edited = fields.Boolean("Is Sales Order Item Manually Edited")
    allow_billable = fields.Boolean(related="project_id.allow_billable")
    sale_order_state = fields.Selection(related='order_id.state')

    @api.depends('project_id.partner_id.commercial_partner_id', 'task_id.partner_id.commercial_partner_id')
    def _compute_commercial_partner(self):
        for timesheet in self:
            timesheet.commercial_partner_id = timesheet.task_id.partner_id.commercial_partner_id or timesheet.project_id.partner_id.commercial_partner_id

    @api.depends('so_line.product_id', 'project_id.billing_type', 'amount')
    def _compute_timesheet_invoice_type(self):
        for timesheet in self:
            if timesheet.project_id:  # AAL will be set to False
                invoice_type = False
                if not timesheet.so_line:
                    invoice_type = 'non_billable' if timesheet.project_id.billing_type != 'manually' else 'billable_manual'
                elif timesheet.so_line.product_id.type == 'service':
                    if timesheet.so_line.product_id.invoice_policy == 'delivery':
                        if timesheet.so_line.product_id.service_type == 'timesheet':
                            invoice_type = 'timesheet_revenues' if timesheet.amount > 0 and timesheet.unit_amount > 0 else 'billable_time'
                        else:
                            service_type = timesheet.so_line.product_id.service_type
                            invoice_type = f'billable_{service_type}' if service_type in ['milestones', 'manual'] else 'billable_fixed'
                    elif timesheet.so_line.product_id.invoice_policy == 'order':
                        invoice_type = 'billable_fixed'
                timesheet.timesheet_invoice_type = invoice_type
            else:
                if timesheet.amount >= 0 and timesheet.unit_amount >= 0:
                    if timesheet.so_line and timesheet.so_line.product_id.type == 'service':
                        timesheet.timesheet_invoice_type = 'service_revenues'
                    else:
                        timesheet.timesheet_invoice_type = 'other_revenues'
                else:
                    timesheet.timesheet_invoice_type = 'other_costs'

    @api.depends('task_id.sale_line_id', 'project_id.sale_line_id', 'employee_id', 'project_id.allow_billable')
    def _compute_so_line(self):
        for timesheet in self.filtered(lambda t: not t.is_so_line_edited and t._is_not_billed()):  # Get only the timesheets are not yet invoiced
            timesheet.so_line = timesheet.project_id.allow_billable and timesheet._timesheet_determine_sale_line()

    @api.depends('timesheet_invoice_id.state')
    def _compute_partner_id(self):
        super(AccountAnalyticLine, self.filtered(lambda t: t._is_not_billed()))._compute_partner_id()

    @api.depends('timesheet_invoice_id.state')
    def _compute_project_id(self):
        super(AccountAnalyticLine, self.filtered(lambda t: t._is_not_billed()))._compute_project_id()

    def _is_readonly(self):
        return super()._is_readonly() or not self._is_not_billed()

    def _is_not_billed(self):
        self.ensure_one()
        return not self.timesheet_invoice_id or self.timesheet_invoice_id.state == 'cancel'

    def _check_timesheet_can_be_billed(self):
        return self.so_line in self.project_id.sale_line_employee_ids.sale_line_id | self.task_id.sale_line_id | self.project_id.sale_line_id

    def _check_can_write(self, values):
        # prevent to update invoiced timesheets if one line is of type delivery
        if self.sudo().filtered(lambda aal: aal.so_line.product_id.invoice_policy == "delivery") and self.filtered(lambda t: t.timesheet_invoice_id and t.timesheet_invoice_id.state != 'cancel'):
            if any(field_name in values for field_name in ['unit_amount', 'employee_id', 'project_id', 'task_id', 'so_line', 'amount', 'date']):
                raise UserError(_('You cannot modify timesheets that are already invoiced.'))
        return super()._check_can_write(values)

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
        return expression.AND([domain, [('timesheet_invoice_type', 'in', ['billable_time', 'non_billable', 'billable_fixed', 'billable_manual', 'billable_milestones'])]])

    @api.model
    def _timesheet_get_sale_domain(self, order_lines_ids, invoice_ids):
        if not invoice_ids:
            return [('so_line', 'in', order_lines_ids.ids)]

        return [
            '|',
            '&',
            ('timesheet_invoice_id', 'in', invoice_ids.ids),
            # TODO : Master: Check if non_billable should be removed ?
            ('timesheet_invoice_type', 'in', ['billable_time', 'non_billable']),
            '&',
            ('timesheet_invoice_type', '=', 'billable_fixed'),
                '&',
                ('so_line', 'in', order_lines_ids.ids),
                ('timesheet_invoice_id', '=', False),
        ]

    def _get_timesheets_to_merge(self):
        res = super()._get_timesheets_to_merge()
        return res.filtered(lambda l: not l.timesheet_invoice_id or l.timesheet_invoice_id.state != 'posted')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_invoiced(self):
        if any(line.timesheet_invoice_id and line.timesheet_invoice_id.state == 'posted' for line in self):
            raise UserError(_('You cannot remove a timesheet that has already been invoiced.'))

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
            'res_id': self.timesheet_invoice_id.id,
        }

    def _timesheet_convert_sol_uom(self, sol, to_unit):
        to_uom = self.env.ref(to_unit)
        return round(sol.product_uom_id._compute_quantity(sol.product_uom_qty, to_uom, raise_if_failure=False), 2)

    def _is_updatable_timesheet(self):
        return super()._is_updatable_timesheet and self._is_not_billed()

    def _timesheet_preprocess_get_accounts(self, vals):
        so_line = self.env['sale.order.line'].browse(vals.get('so_line'))
        if not (so_line and (distribution := so_line.analytic_distribution)):
            return super()._timesheet_preprocess_get_accounts(vals)

        company = self.env['res.company'].browse(vals.get('company_id'))
        accounts = self.env['account.analytic.account'].browse([
            int(account_id) for account_id in next(iter(distribution)).split(',')
        ])

        plan_column_names = {account.root_plan_id._column_name() for account in accounts}
        mandatory_plans = [plan for plan in self._get_mandatory_plans(company, business_domain='timesheet') if plan['column_name'] != 'account_id']
        missing_plan_names = [plan['name'] for plan in mandatory_plans if plan['column_name'] not in plan_column_names]
        if missing_plan_names:
            raise ValidationError(_(
                "'%(missing_plan_names)s' analytic plan(s) required on the analytic distribution of the sale order item '%(so_line_name)s' linked to the timesheet.",
                missing_plan_names=format_list(self.env, missing_plan_names),
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
