# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.models import Query
from odoo.tools import SQL
from odoo.tools.misc import unquote
from odoo.tools.translate import _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _domain_sale_line_id(self):
        domain = Domain.AND([
            self.env['sale.order.line']._sellable_lines_domain(),
            self.env['sale.order.line']._domain_sale_line_service(),
            [
            '|',
                ('order_partner_id.commercial_partner_id.id', 'parent_of', unquote('partner_id if partner_id else []')),
                ('order_partner_id', '=?', unquote('partner_id')),
            ],
        ])
        return domain

    allow_billable = fields.Boolean("Billable")
    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item', copy=False,
        compute="_compute_sale_line_id", store=True, readonly=False, index='btree_not_null',
        domain=lambda self: str(self._domain_sale_line_id()),
        help="Sales order item that will be selected by default on the tasks and timesheets of this project,"
            " except if the employee set on the timesheets is explicitely linked to another sales order item on the project.\n"
            "It can be modified on each task and timesheet entry individually if necessary.")
    sale_order_id = fields.Many2one(related='sale_line_id.order_id', export_string_translation=False)
    has_any_so_to_invoice = fields.Boolean('Has SO to Invoice', compute='_compute_has_any_so_to_invoice', export_string_translation=False)
    sale_order_line_count = fields.Integer(compute='_compute_sale_order_count', groups='sales_team.group_sale_salesman', export_string_translation=False)
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', groups='sales_team.group_sale_salesman', export_string_translation=False)
    has_any_so_with_nothing_to_invoice = fields.Boolean('Has a SO with an invoice status of No', compute='_compute_has_any_so_with_nothing_to_invoice', export_string_translation=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count', groups='account.group_account_readonly', export_string_translation=False)
    vendor_bill_count = fields.Integer(related='account_id.vendor_bill_count', groups='account.group_account_readonly', compute_sudo=False, export_string_translation=False)
    partner_id = fields.Many2one(compute="_compute_partner_id", store=True, readonly=False)
    display_sales_stat_buttons = fields.Boolean(compute='_compute_display_sales_stat_buttons', export_string_translation=False)
    sale_order_state = fields.Selection(related='sale_order_id.state', export_string_translation=False)
    reinvoiced_sale_order_id = fields.Many2one('sale.order', string='Sales Order', groups='sales_team.group_sale_salesman', copy=False, domain="[('partner_id', '=', partner_id)]", index='btree_not_null',
        help="Products added to stock pickings, whose operation type is configured to generate analytic costs, will be re-invoiced in this sales order if they are set up for it.",
    )
    actual_margin = fields.Monetary(compute='_compute_actual_margin', export_string_translation=False)

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if self.env.context.get('order_state') == 'sale':
            order_id = self.env.context.get('order_id')
            sale_line_id = self.env['sale.order.line'].search(
                [('order_id', '=', order_id), ('is_service', '=', True)],
                limit=1).id
            defaults.update({
                'reinvoiced_sale_order_id': order_id,
                'sale_line_id': sale_line_id,
            })
        return defaults

    @api.model
    def _map_tasks_default_values(self, project):
        defaults = super()._map_tasks_default_values(project)
        defaults['sale_line_id'] = False
        return defaults

    @api.depends('allow_billable', 'partner_id.company_id')
    def _compute_partner_id(self):
        for project in self:
            # Ensures that the partner_id and its project do not have different companies set
            if not project.allow_billable or (project.company_id and project.partner_id.company_id and project.company_id != project.partner_id.company_id):
                project.partner_id = False

    @api.depends('partner_id')
    def _compute_sale_line_id(self):
        self.filtered(
            lambda p:
                p.sale_line_id and (
                    not p.partner_id or p.sale_line_id.order_partner_id.commercial_partner_id != p.partner_id.commercial_partner_id
                )
        ).update({'sale_line_id': False})

    def _get_projects_for_invoice_status(self, invoice_status):
        """ Returns a recordset of project.project that has any Sale Order which invoice_status is the same as the
            provided invoice_status.

            :param invoice_status: The invoice status.
        """
        result = self.env.execute_query(SQL("""
            SELECT id
              FROM project_project pp
             WHERE pp.active = true
               AND (   EXISTS(SELECT 1
                                FROM sale_order so
                                JOIN project_task pt ON pt.sale_order_id = so.id
                               WHERE pt.project_id = pp.id
                                 AND pt.active = true
                                 AND so.invoice_status = %(invoice_status)s)
                    OR EXISTS(SELECT 1
                                FROM sale_order so
                                JOIN sale_order_line sol ON sol.order_id = so.id
                               WHERE sol.id = pp.sale_line_id
                                 AND so.invoice_status = %(invoice_status)s))
               AND id in %(ids)s""", ids=tuple(self.ids), invoice_status=invoice_status))
        return self.env['project.project'].browse(id_ for id_, in result)

    @api.depends('sale_order_id.invoice_status', 'tasks.sale_order_id.invoice_status')
    def _compute_has_any_so_to_invoice(self):
        """Has any Sale Order whose invoice_status is set as To Invoice"""
        if not self.ids:
            self.has_any_so_to_invoice = False
            return

        project_to_invoice = self._get_projects_for_invoice_status('to invoice')
        project_to_invoice.has_any_so_to_invoice = True
        (self - project_to_invoice).has_any_so_to_invoice = False

    @api.depends('sale_order_id', 'task_ids.sale_order_id')
    def _compute_sale_order_count(self):
        sale_order_items_per_project_id = self._fetch_sale_order_items_per_project_id({'project.task': [('is_closed', '=', False)]})
        for project in self:
            sale_order_lines = sale_order_items_per_project_id.get(project.id, self.env['sale.order.line'])
            project.sale_order_line_count = len(sale_order_lines)

            # Use sudo to avoid AccessErrors when the SOLs belong to different companies.
            project.sale_order_count = len(sale_order_lines.sudo().order_id or project.reinvoiced_sale_order_id)

    def _compute_invoice_count(self):
        data = self.env['account.move.line']._read_group(
            [('move_id.move_type', 'in', ['out_invoice', 'out_refund']), ('analytic_distribution', 'in', self.account_id.ids)],
            groupby=['analytic_distribution'],
            aggregates=['__count'],
        )
        data = {int(account_id): move_count for account_id, move_count in data}
        for project in self:
            project.invoice_count = data.get(project.account_id.id, 0)

    @api.depends('allow_billable', 'partner_id')
    def _compute_display_sales_stat_buttons(self):
        for project in self:
            project.display_sales_stat_buttons = project.allow_billable and project.partner_id

    def _compute_actual_margin(self):
        margin_per_account = dict(self.env['account.analytic.line']._read_group(
            domain=[('account_id', 'in', self.account_id.ids)],
            groupby=['account_id'],
            aggregates=['amount:sum'],
        ))
        for project in self:
            project.actual_margin = margin_per_account.get(project.account_id.id, 0.0)

    def action_customer_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    @api.onchange('reinvoiced_sale_order_id')
    def _onchange_reinvoiced_sale_order_id(self):
        if (
            not self.sale_line_id
            and (service_sols := self.reinvoiced_sale_order_id.order_line.filtered('is_service'))
        ):
            self.sale_line_id = service_sols[0]

    @api.onchange('sale_line_id')
    def _onchange_sale_line_id(self):
        if not self.reinvoiced_sale_order_id and self.sale_line_id:
            self.reinvoiced_sale_order_id = self.sale_line_id.order_id

    def _ensure_sale_order_linked(self, sol_ids):
        """ Orders created from project/task are supposed to be confirmed to match the typical flow from sales, but since
        we allow SO creation from the project/task itself we want to confirm newly created SOs immediately after creation.
        However this would leads to SOs being confirmed without a single product, so we'd rather do it on record save.
        """
        quotations = self.env['sale.order.line'].sudo()._read_group(
            domain=[('state', '=', 'draft'), ('id', 'in', sol_ids)],
            aggregates=['order_id:recordset'],
        )[0][0]
        if quotations:
            quotations.action_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        sol_ids = set()
        for project, vals in zip(projects, vals_list):
            if (vals.get('sale_line_id')):
                sol_ids.add(vals['sale_line_id'])
            if project.sale_order_id and not project.sale_order_id.project_id:
                project.sale_order_id.project_id = project.id
            elif project.sudo().reinvoiced_sale_order_id and not project.sudo().reinvoiced_sale_order_id.project_id:
                project.sudo().reinvoiced_sale_order_id.project_id = project.id
        if sol_ids:
            projects._ensure_sale_order_linked(list(sol_ids))
        return projects

    def write(self, vals):
        project = super().write(vals)
        if sol_id := vals.get('sale_line_id'):
            self._ensure_sale_order_linked([sol_id])
        return project

    def _get_sale_orders_domain(self, all_sale_orders):
        return [("id", "in", all_sale_orders.ids)]

    def _get_view_action(self):
        return self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")

    def action_view_sols(self):
        self.ensure_one()
        all_sale_order_lines = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
        action_window = {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'name': self.env._("Sales Order Items"),
            'context': {
                'show_sale': True,
                'link_to_project': self.id,
                'form_view_ref': 'sale_project.sale_order_line_view_form_editable',  # Necessary for some logic in the form view
                'action_view_sols': True,
                'default_partner_id': self.partner_id.id,
                'default_company_id': self.company_id.id,
                'default_order_id': self.sale_order_id.id,
            },
            'views': [(self.env.ref('sale_project.sale_order_line_view_form_editable').id, 'form')],
        }
        if len(all_sale_order_lines) <= 1:
            action_window['res_id'] = all_sale_order_lines.id
        if len(all_sale_order_lines) > 1 or not self.partner_id:
            action_window.update({
                'domain': [('id', 'in', all_sale_order_lines.ids)],
                'views': [
                    (self.env.ref('sale_project.view_order_line_tree_with_create').id, 'list'),
                    (self.env.ref('sale_project.sale_order_line_view_form_editable').id, 'form'),
                ],
            })
            if not self.partner_id:
                action_window['context'].update({'create': False})
        return action_window

    def action_view_sos(self):
        self.ensure_one()
        all_sale_orders = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]}).sudo().order_id
        embedded_action_context = self.env.context.get('from_embedded_action', False)
        action_window = self._get_view_action()
        action_window["domain"] = self._get_sale_orders_domain(all_sale_orders)
        action_window['context'] = {
            **ast.literal_eval(action_window['context']),
            "create": self.env.context.get("create_for_project_id", embedded_action_context),
            "show_sale": True,
            "default_partner_id": self.partner_id.id,
            "default_project_id": self.id,
            "create_for_project_id": self.id if not embedded_action_context else False,
            "from_embedded_action": embedded_action_context,
        }
        if len(all_sale_orders) <= 1 and not embedded_action_context:
            action_window.update({
                "res_id": all_sale_orders.id,
                "views": [[False, "form"]],
            })
        return action_window

    def action_get_list_view(self):
        action = super().action_get_list_view()
        if self.allow_billable:
            action['views'] = [(self.env.ref('sale_project.project_milestone_view_tree').id, view_type) if view_type == 'list' else (view_id, view_type) for view_id, view_type in action['views']]
        return action

    @api.depends('sale_order_id.invoice_status', 'tasks.sale_order_id.invoice_status')
    def _compute_has_any_so_with_nothing_to_invoice(self):
        """Has any Sale Order whose invoice_status is set as No"""
        if not self.ids:
            self.has_any_so_with_nothing_to_invoice = False
            return

        project_nothing_to_invoice = self._get_projects_for_invoice_status('no')
        project_nothing_to_invoice.has_any_so_with_nothing_to_invoice = True
        (self - project_nothing_to_invoice).has_any_so_with_nothing_to_invoice = False

    def action_create_invoice(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_view_sale_advance_payment_inv")
        so_ids = (self.sale_order_id | self.task_ids.sale_order_id).filtered(lambda so: so.invoice_status in ['to invoice', 'no']).ids
        action['context'] = {
            'active_id': so_ids[0] if len(so_ids) == 1 else False,
            'active_ids': so_ids
        }
        if not self.has_any_so_to_invoice:
            action['context']['default_advance_payment_method'] = 'percentage'
        return action

    def action_open_project_invoices(self):
        move_lines = self.env['account.move.line'].search_fetch(
            [
                ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                ('analytic_distribution', 'in', self.account_id.ids),
            ],
            ['move_id'],
        )
        invoice_ids = move_lines.move_id.ids
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', invoice_ids)],
            'context': {
                'default_move_type': 'out_invoice',
                'default_partner_id': self.partner_id.id,
                'project_id': self.id
            },
            'help': "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>" %
            (_("Create a customer invoice"),
                _("Create invoices, register payments and keep track of the discussions with your customers."))
        }
        if len(invoice_ids) == 1 and not self.env.context.get('from_embedded_action', False):
            action['views'] = [[False, 'form']]
            action['res_id'] = invoice_ids[0]
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _fetch_sale_order_items_per_project_id(self, domain_per_model=None):
        if not self:
            return {}
        if len(self) == 1:
            return {self.id: self._fetch_sale_order_items(domain_per_model)}
        sql = self._get_sale_order_items_query(domain_per_model).select('id', 'ARRAY_AGG(DISTINCT sale_line_id) AS sale_line_ids')
        sql = SQL("%s GROUP BY id", sql)
        return {
            id_: self.env['sale.order.line'].browse(sale_line_ids)
            for id_, sale_line_ids in self.env.execute_query(sql)
        }

    def _fetch_sale_order_items(self, domain_per_model=None, limit=None, offset=None):
        return self.env['sale.order.line'].browse(self._fetch_sale_order_item_ids(domain_per_model, limit, offset))

    def _fetch_sale_order_item_ids(self, domain_per_model=None, limit=None, offset=None):
        if not self or not self.filtered('allow_billable'):
            return []
        query = self._get_sale_order_items_query(domain_per_model)
        query.limit = limit
        query.offset = offset
        return [id_ for id_, in self.env.execute_query(query.select('DISTINCT sale_line_id'))]

    def _get_sale_orders(self):
        return self._get_sale_order_items().order_id

    def _get_sale_order_items(self):
        return self._fetch_sale_order_items()

    def _get_sale_order_items_query(self, domain_per_model=None):
        if domain_per_model is None:
            domain_per_model = {}
        billable_project_domain = [('allow_billable', '=', True)]
        project_domain = [('id', 'in', self.ids), ('sale_line_id', '!=', False)]
        if 'project.project' in domain_per_model:
            project_domain = Domain.AND([
                domain_per_model['project.project'],
                project_domain,
                billable_project_domain,
            ])
        project_query = self.env['project.project']._search(project_domain)
        project_sql = project_query.select(f'{self._table}.id ', f'{self._table}.sale_line_id')

        Task = self.env['project.task']
        task_domain = [('project_id', 'in', self.ids), ('sale_line_id', '!=', False)]
        if Task._name in domain_per_model:
            task_domain = Domain.AND([
                domain_per_model[Task._name],
                task_domain,
            ])
        task_query = Task._search(task_domain)
        task_sql = task_query.select(f'{Task._table}.project_id AS id', f'{Task._table}.sale_line_id')

        ProjectMilestone = self.env['project.milestone']
        milestone_domain = [('project_id', 'in', self.ids), ('allow_billable', '=', True), ('sale_line_id', '!=', False)]
        if ProjectMilestone._name in domain_per_model:
            milestone_domain = Domain.AND([
                domain_per_model[ProjectMilestone._name],
                milestone_domain,
                billable_project_domain,
            ])
        milestone_query = ProjectMilestone._search(milestone_domain)
        milestone_sql = milestone_query.select(
            f'{ProjectMilestone._table}.project_id AS id',
            f'{ProjectMilestone._table}.sale_line_id',
        )

        SaleOrderLine = self.env['sale.order.line']
        sale_order_line_domain = [
            '&',
                ('display_type', '=', False),
                ('order_id', 'any', ['|',
                    ('id', 'in', self.reinvoiced_sale_order_id.ids),
                    ('project_id', 'in', self.ids),
                ]),
        ]
        sale_order_line_query = SaleOrderLine._search(sale_order_line_domain, bypass_access=True)
        sale_order_line_sql = sale_order_line_query.select(
            f'{SaleOrderLine._table}.project_id AS id',
            f'{SaleOrderLine._table}.id AS sale_line_id',
        )

        return Query(None, 'project_sale_order_item', SQL('(%s)', SQL(' UNION ').join([
            project_sql, task_sql, milestone_sql, sale_order_line_sql,
        ])))

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    def _get_hide_partner(self):
        return not self.allow_billable

    def _get_projects_to_make_billable_domain(self):
        return Domain.AND([
            super()._get_projects_to_make_billable_domain(),
            [('allow_billable', '=', False)],
        ])

    def action_view_tasks(self):
        if self.env.context.get('generate_milestone'):
            line_id = self.env.context.get('default_sale_line_id')
            default_line = self.env['sale.order.line'].browse(line_id)
            milestone = self.env['project.milestone'].create({
                'name': default_line.name,
                'project_id': self.id,
                'sale_line_id': line_id,
                'quantity_percentage': 1,
            })
            if default_line.product_id.service_tracking == 'task_in_project':
                default_line.task_id.milestone_id = milestone.id

        action = super().action_view_tasks()
        action['context']['hide_partner'] = self._get_hide_partner()
        action['context']['allow_billable'] = self.allow_billable
        if self.env.context.get("from_sale_order_action"):
            context = dict(action.get("context", {}))
            context.pop("search_default_open_tasks", None)
            if sale_order_id := self.env.context.get('default_reinvoiced_sale_order_id') or self.reinvoiced_sale_order_id.id:
                context["search_default_sale_order_id"] = sale_order_id
            if not self.sale_order_id:
                sale_order = self.env["sale.order"].browse(self.env.context.get("active_id"))
                context["default_sale_order_id"] = sale_order.id
            action["context"] = context
        return action

    def action_open_project_vendor_bills(self):
        move_lines = self.env['account.move.line'].search_fetch(
            [
                ('parent_state', '!=', 'cancel'),
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('analytic_distribution', 'in', self.account_id.ids),
            ],
            ['move_id'],
        )
        vendor_bill_ids = move_lines.move_id.ids
        action_window = {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'list'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', vendor_bill_ids)],
            'context': {
                'default_move_type': 'in_invoice',
                'project_id': self.id,
            },
            'help': "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>" % (
                _("Create a vendor bill"),
                _("Create invoices, register payments and keep track of the discussions with your vendors."),
            ),
        }
        if not self.env.context.get('from_embedded_action') and len(vendor_bill_ids) == 1:
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = vendor_bill_ids[0]
        return action_window

    def _fetch_products_linked_to_template(self, limit=None):
        self.ensure_one()
        return self.env['product.template'].search([('project_template_id', '=', self.id)], limit=limit)

    def template_to_project_confirmation_callback(self, callbacks):
        super().template_to_project_confirmation_callback(callbacks)
        if callbacks.get('unlink_template_products'):
            self._fetch_products_linked_to_template().project_template_id = False

    def _get_template_to_project_confirmation_callbacks(self):
        callbacks = super()._get_template_to_project_confirmation_callbacks()
        if self._fetch_products_linked_to_template(limit=1):
            callbacks['unlink_template_products'] = True
        return callbacks

    def _get_template_to_project_warnings(self):
        self.ensure_one()
        res = super()._get_template_to_project_warnings()
        if self.is_template and self._fetch_products_linked_to_template(limit=1):
            res.append(self.env._('Converting this template to a regular project will unlink it from its associated products.'))
        return res

    def _get_template_default_context_whitelist(self):
        return [
            *super()._get_template_default_context_whitelist(),
            'allow_billable',
            'from_sale_order_action',
        ]

    def action_actual_margin(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sale_project.action_analytic_reporting_inherit_sale_project')
        action['display_name'] = self.env._("%(name)s's Actual Margins", name=self.name)
        action['context'] = {'search_default_fiscal_date': 1, 'search_default_group_date': 1}
        action['domain'] = [('account_id', 'in', self.account_id.ids)]
        return action
