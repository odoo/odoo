# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict

from odoo import api, fields, models, _, _lt
from odoo.osv import expression
from odoo.tools import Query, SQL


class ProjectProject(models.Model):
    _inherit = 'project.project'

    allow_billable = fields.Boolean("Billable")
    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item', copy=False,
        compute="_compute_sale_line_id", store=True, readonly=False, index='btree_not_null',
        domain=lambda self: self.env['sale.order.line']._domain_sale_line_service_str("[('order_partner_id', '=?', partner_id)]"),
        help="Sales order item that will be selected by default on the tasks and timesheets of this project,"
            " except if the employee set on the timesheets is explicitely linked to another sales order item on the project.\n"
            "It can be modified on each task and timesheet entry individually if necessary.")
    sale_order_id = fields.Many2one(string='Sales Order', related='sale_line_id.order_id', help="Sales order to which the project is linked.")
    has_any_so_to_invoice = fields.Boolean('Has SO to Invoice', compute='_compute_has_any_so_to_invoice')
    sale_order_line_count = fields.Integer(compute='_compute_sale_order_count', groups='sales_team.group_sale_salesman')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', groups='sales_team.group_sale_salesman')
    has_any_so_with_nothing_to_invoice = fields.Boolean('Has a SO with an invoice status of No', compute='_compute_has_any_so_with_nothing_to_invoice')
    invoice_count = fields.Integer(compute='_compute_invoice_count', groups='account.group_account_readonly')
    vendor_bill_count = fields.Integer(related='analytic_account_id.vendor_bill_count', groups='account.group_account_readonly')
    partner_id = fields.Many2one(compute="_compute_partner_id", store=True, readonly=False)
    display_sales_stat_buttons = fields.Boolean(compute='_compute_display_sales_stat_buttons')
    sale_order_state = fields.Selection(related='sale_order_id.state')

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
        self.env.cr.execute("""
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
               AND id in %(ids)s""", {'ids': tuple(self.ids), 'invoice_status': invoice_status})
        return self.env['project.project'].browse([x[0] for x in self.env.cr.fetchall()])

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
            project.sale_order_count = len(sale_order_lines.order_id)

    def _compute_invoice_count(self):
        data = self.env['account.move.line']._read_group(
            [('move_id.move_type', 'in', ['out_invoice', 'out_refund']), ('analytic_distribution', 'in', self.analytic_account_id.ids)],
            groupby=['analytic_distribution'],
            aggregates=['__count'],
        )
        data = {int(account_id): move_count for account_id, move_count in data}
        for project in self:
            project.invoice_count = data.get(project.analytic_account_id.id, 0)

    @api.depends('allow_billable', 'partner_id')
    def _compute_display_sales_stat_buttons(self):
        for project in self:
            project.display_sales_stat_buttons = project.allow_billable and project.partner_id

    def action_view_sols(self):
        self.ensure_one()
        all_sale_order_lines = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]})
        action_window = {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'name': _("%(name)s's Sales Order Items", name=self.name),
            'context': {
                'show_sale': True,
                'link_to_project': self.id,
                'form_view_ref': 'sale_project.sale_order_line_view_form_editable',  # Necessary for some logic in the form view
                'default_partner_id': self.partner_id.id,
                'default_company_id': self.company_id.id,
                'default_order_id': self.sale_order_id.id,
            },
            'views': [(self.env.ref('sale_project.sale_order_line_view_form_editable').id, 'form')],
        }
        if len(all_sale_order_lines) <= 1:
            action_window['res_id'] = all_sale_order_lines.id
        else:
            action_window.update({
                'domain': [('id', 'in', all_sale_order_lines.ids)],
                'views': [
                    (self.env.ref('sale_project.view_order_line_tree_with_create').id, 'tree'),
                    (self.env.ref('sale_project.sale_order_line_view_form_editable').id, 'form'),
                ],
            })
        return action_window

    def action_view_sos(self):
        self.ensure_one()
        all_sale_orders = self._fetch_sale_order_items({'project.task': [('is_closed', '=', False)]}).order_id
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            'name': _("%(name)s's Sales Orders", name=self.name),
            "context": {"create": self.env.context.get('create_for_project_id', False), "show_sale": True},
        }
        if len(all_sale_orders) <= 1:
            action_window.update({
                "res_id": all_sale_orders.id,
                "views": [[False, "form"]],
            })
        else:
            action_window.update({
                "domain": [('id', 'in', all_sale_orders.ids)],
                "views": [[False, "tree"], [False, "kanban"], [False, "calendar"], [False, "pivot"],
                           [False, "graph"], [False, "activity"], [False, "form"]],
            })
        return action_window

    def action_get_list_view(self):
        action = super().action_get_list_view()
        if self.allow_billable:
            action['views'] = [(self.env.ref('sale_project.project_milestone_view_tree').id, 'tree'), (False, 'form')]
        return action

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name in ['service_revenues', 'materials']:
            view_types = ['list', 'kanban', 'form']
            action = {
                'name': _('Sales Order Items'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order.line',
                'context': {'create': False, 'edit': False},
            }
            if res_id:
                action['res_id'] = res_id
                view_types = ['form']
            else:
                action['domain'] = domain
            action['views'] = [(False, v) for v in view_types]
            return action

        if section_name in ['other_invoice_revenues', 'downpayments']:
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
            action['domain'] = domain if domain else []
            if res_id:
                action['views'] = [(False, 'form')]
                action['view_mode'] = 'form'
                action['res_id'] = res_id
            return action

        return super().action_profitability_items(section_name, domain, res_id)

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
                ('analytic_distribution', 'in', self.analytic_account_id.ids),
            ],
            ['move_id'],
        )
        invoice_ids = move_lines.move_id.ids
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', invoice_ids)],
            'context': {
                'create': False,
            }
        }
        if len(invoice_ids) == 1:
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
        query_str, params = self._get_sale_order_items_query(domain_per_model).select('id', 'ARRAY_AGG(DISTINCT sale_line_id) AS sale_line_ids')
        query = f"""
            {query_str}
            GROUP BY id
        """
        self._cr.execute(query, params)
        return {row['id']: self.env['sale.order.line'].browse(row['sale_line_ids']) for row in self._cr.dictfetchall()}

    def _fetch_sale_order_items(self, domain_per_model=None, limit=None, offset=None):
        return self.env['sale.order.line'].browse(self._fetch_sale_order_item_ids(domain_per_model, limit, offset))

    def _fetch_sale_order_item_ids(self, domain_per_model=None, limit=None, offset=None):
        if not self or not self.filtered('allow_billable'):
            return []
        query = self._get_sale_order_items_query(domain_per_model)
        query.limit = limit
        query.offset = offset
        rows = self.env.execute_query(query.select('DISTINCT sale_line_id'))
        return [row[0] for row in rows]

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
            project_domain = expression.AND([
                domain_per_model['project.project'],
                project_domain,
                billable_project_domain,
            ])
        project_query = self.env['project.project']._where_calc(project_domain)
        self._apply_ir_rules(project_query, 'read')
        project_sql = project_query.select('id', 'sale_line_id')

        Task = self.env['project.task']
        task_domain = [('project_id', 'in', self.ids), ('sale_line_id', '!=', False)]
        if Task._name in domain_per_model:
            task_domain = expression.AND([
                domain_per_model[Task._name],
                task_domain,
            ])
        task_query = Task._where_calc(task_domain)
        Task._apply_ir_rules(task_query, 'read')
        task_sql = task_query.select(f'{Task._table}.project_id AS id', f'{Task._table}.sale_line_id')

        ProjectMilestone = self.env['project.milestone']
        milestone_domain = [('project_id', 'in', self.ids), ('allow_billable', '=', True), ('sale_line_id', '!=', False)]
        if ProjectMilestone._name in domain_per_model:
            milestone_domain = expression.AND([
                domain_per_model[ProjectMilestone._name],
                milestone_domain,
                billable_project_domain,
            ])
        milestone_query = ProjectMilestone._where_calc(milestone_domain)
        ProjectMilestone._apply_ir_rules(milestone_query)
        milestone_sql = milestone_query.select(
            f'{ProjectMilestone._table}.project_id AS id',
            f'{ProjectMilestone._table}.sale_line_id',
        )

        SaleOrderLine = self.env['sale.order.line']
        sale_order_line_domain = [('order_id', 'any', [('analytic_account_id', 'in', self.analytic_account_id.ids)])]
        sale_order_line_query = SaleOrderLine._where_calc(sale_order_line_domain)
        sale_order_line_sql = sale_order_line_query.select(
            f'{SaleOrderLine._table}.project_id AS id',
            f'{SaleOrderLine._table}.id AS sale_line_id',
        )

        return Query(self.env, 'project_sale_order_item', SQL('(%s)', SQL(' UNION ').join([
            project_sql, task_sql, milestone_sql, sale_order_line_sql,
        ])))

    def get_panel_data(self):
        panel_data = super().get_panel_data()
        return {
            **panel_data,
            'sale_items': self._get_sale_items() if self.allow_billable else {},
        }

    def get_sale_items_data(self, domain=None, offset=0, limit=None, with_action=True):
        if not self.env.user.has_group('project.group_project_user'):
            return {}
        sols = self.env['sale.order.line'].sudo().search(
            domain or self._get_sale_items_domain(),
            offset=offset,
            limit=limit,
        )
        # filter to only get the action for the SOLs that the user can read
        action_per_sol = sols.sudo(False)._filter_access_rules_python('read')._get_action_per_item() if with_action else {}

        def get_action(sol_id):
            """ Return the action vals to call it in frontend if the user can access to the SO related """
            action, res_id = action_per_sol.get(sol_id, (None, None))
            return {'action': {'name': action, 'resId': res_id, 'buttonContext': json.dumps({'active_id': sol_id, 'default_project_id': self.id})}} if action else {}

        return [{
            **sol_read,
            **get_action(sol_read['id']),
        } for sol_read in sols.with_context(with_price_unit=True).read(['display_name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom'])]

    def _get_sale_items_domain(self, additional_domain=None):
        sale_items = self.sudo()._get_sale_order_items()
        domain = [
            ('order_id', 'in', sale_items.sudo().order_id.ids),
            ('is_downpayment', '=', False),
            ('state', '=', 'sale'),
            ('display_type', '=', False),
            '|',
                '|',
                    ('project_id', 'in', self.ids),
                    ('project_id', '=', False),
                ('id', 'in', sale_items.ids),
        ]
        if additional_domain:
            domain = expression.AND([domain, additional_domain])
        return domain

    def _get_sale_items(self, with_action=True):
        domain = self._get_sale_items_domain()
        return {
            'total': self.env['sale.order.line'].sudo().search_count(domain),
            'data': self.get_sale_items_data(domain, limit=5, with_action=with_action),
        }

    def _show_profitability(self):
        self.ensure_one()
        return self.allow_billable and super()._show_profitability()

    def _show_profitability_helper(self):
        return True

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            'service_revenues': _lt('Other Services'),
            'materials': _lt('Materials'),
            'other_invoice_revenues': _lt('Customer Invoices'),
            'downpayments': _lt('Down Payments'),
        }

    def _get_profitability_sequence_per_invoice_type(self):
        return {
            **super()._get_profitability_sequence_per_invoice_type(),
            'service_revenues': 6,
            'materials': 7,
            'other_invoice_revenues': 9,
            'downpayments': 20,
        }

    def _get_service_policy_to_invoice_type(self):
        return {
            'ordered_prepaid': 'service_revenues',
            'delivered_milestones': 'service_revenues',
            'delivered_manual': 'service_revenues',
        }

    def _get_profitability_sale_order_items_domain(self, domain=None):
        if domain is None:
            domain = []
        return expression.AND([
            [
                '|', ('product_id', '!=', False), ('is_downpayment', '=', True),
                ('is_expense', '=', False),
                ('state', '=', 'sale'),
                '|', ('qty_to_invoice', '>', 0), ('qty_invoiced', '>', 0),
            ],
            domain,
        ])

    def _get_revenues_items_from_sol(self, domain=None, with_action=True):
        sale_line_read_group = self.env['sale.order.line'].sudo()._read_group(
            self._get_profitability_sale_order_items_domain(domain),
            ['currency_id', 'product_id', 'is_downpayment'],
            ['id:array_agg', 'untaxed_amount_to_invoice:sum', 'untaxed_amount_invoiced:sum'],
        )
        display_sol_action = with_action and len(self) == 1 and self.env.user.has_group('sales_team.group_sale_salesman')
        revenues_dict = {}
        total_to_invoice = total_invoiced = 0.0
        data = []
        sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()
        if sale_line_read_group:
            # Get conversion rate from currencies of the sale order lines to currency of project
            convert_company = self.company_id or self.env.company

            sols_per_product = defaultdict(lambda: [0.0, 0.0, []])
            downpayment_amount_invoiced = 0
            downpayment_sol_ids = []
            for currency, product, is_downpayment, sol_ids, untaxed_amount_to_invoice, untaxed_amount_invoiced in sale_line_read_group:
                if is_downpayment:
                    downpayment_amount_invoiced += currency._convert(untaxed_amount_invoiced, convert_company.currency_id, convert_company, round=False)
                    downpayment_sol_ids += sol_ids
                else:
                    sols_per_product[product.id][0] += currency._convert(untaxed_amount_to_invoice, convert_company.currency_id, convert_company)
                    sols_per_product[product.id][1] += currency._convert(untaxed_amount_invoiced, convert_company.currency_id, convert_company)
                    sols_per_product[product.id][2] += sol_ids
            if downpayment_amount_invoiced:
                downpayments_data = {
                    'id': 'downpayments',
                    'sequence': sequence_per_invoice_type['downpayments'],
                    'invoiced': downpayment_amount_invoiced,
                    'to_invoice': -downpayment_amount_invoiced
                }
                if with_action and (
                    self.env.user.has_group('sales_team.group_sale_salesman_all_leads,')
                    or self.env.user.has_group('account.group_account_invoice,')
                    or self.env.user.has_group('account.group_account_readonly')
                ):
                    invoices = self.env['account.move'].search([('line_ids.sale_line_ids', 'in', downpayment_sol_ids)])
                    args = ['downpayments', [('id', 'in', invoices.ids)]]
                    if len(invoices) == 1:
                        args.append(invoices.id)
                    downpayments_data['action'] = {
                        'name': 'action_profitability_items',
                        'type': 'object',
                        'args': json.dumps(args),
                    }
                data += [downpayments_data]
                total_invoiced += downpayment_amount_invoiced
                total_to_invoice -= downpayment_amount_invoiced
            product_read_group = self.env['product.product'].sudo()._read_group(
                [('id', 'in', list(sols_per_product))],
                ['invoice_policy', 'service_type', 'type'],
                ['id:array_agg'],
            )
            service_policy_to_invoice_type = self._get_service_policy_to_invoice_type()
            general_to_service_map = self.env['product.template']._get_general_to_service_map()
            for invoice_policy, service_type, type_, product_ids in product_read_group:
                service_policy = None
                if type_ == 'service':
                    service_policy = general_to_service_map.get(
                        (invoice_policy, service_type),
                        'ordered_prepaid')
                for product_id, (amount_to_invoice, amount_invoiced, sol_ids) in sols_per_product.items():
                    if product_id in product_ids:
                        invoice_type = service_policy_to_invoice_type.get(service_policy, 'materials')
                        revenue = revenues_dict.setdefault(invoice_type, {'invoiced': 0.0, 'to_invoice': 0.0})
                        revenue['to_invoice'] += amount_to_invoice
                        total_to_invoice += amount_to_invoice
                        revenue['invoiced'] += amount_invoiced
                        total_invoiced += amount_invoiced
                        if display_sol_action and invoice_type in ['service_revenues', 'materials']:
                            revenue.setdefault('record_ids', []).extend(sol_ids)

            if display_sol_action:
                section_name = 'materials'
                materials = revenues_dict.get(section_name, {})
                sale_order_items = self.env['sale.order.line'] \
                    .browse(materials.pop('record_ids', [])) \
                    ._filter_access_rules_python('read')
                if sale_order_items:
                    args = [section_name, [('id', 'in', sale_order_items.ids)]]
                    if len(sale_order_items) == 1:
                        args.append(sale_order_items.id)
                    action_params = {
                        'name': 'action_profitability_items',
                        'type': 'object',
                        'args': json.dumps(args),
                    }
                    if len(sale_order_items) == 1:
                        action_params['res_id'] = sale_order_items.id
                    materials['action'] = action_params
        sequence_per_invoice_type = self._get_profitability_sequence_per_invoice_type()
        data += [{
            'id': invoice_type,
            'sequence': sequence_per_invoice_type[invoice_type],
            **vals,
        } for invoice_type, vals in revenues_dict.items()]
        return {
            'data': data,
            'total': {'to_invoice': total_to_invoice, 'invoiced': total_invoiced},
        }

    def _get_revenues_items_from_invoices_domain(self, domain=None):
        if domain is None:
            domain = []
        return expression.AND([
            domain,
            [('move_id.move_type', 'in', self.env['account.move'].get_sale_types()),
            ('parent_state', 'in', ['draft', 'posted']),
            ('price_subtotal', '!=', 0),
            ('is_downpayment', '=', False)],
        ])

    def _get_revenues_items_from_invoices(self, excluded_move_line_ids=None, with_action=True):
        """
        Get all revenues items from invoices, and put them into their own
        "other_invoice_revenues" section.
        If the final total is 0 for either to_invoice or invoiced (ex: invoice -> credit note),
        we don't output a new section

        :param excluded_move_line_ids a list of 'account.move.line' to ignore
        when fetching the move lines, for example a list of invoices that were
        generated from a sales order
        """
        if excluded_move_line_ids is None:
            excluded_move_line_ids = []
        invoices_move_lines = self.env['account.move.line'].sudo().search_fetch(
            expression.AND([
                self._get_revenues_items_from_invoices_domain([('id', 'not in', excluded_move_line_ids)]),
                [('analytic_distribution', 'in', self.analytic_account_id.ids)]
            ]),
            ['price_subtotal', 'parent_state', 'currency_id', 'analytic_distribution', 'move_type', 'move_id']
        )
        # TODO: invoices_move_lines.with_context(prefetch_fields=False).move_id.move_type ??
        if invoices_move_lines:
            amount_invoiced = amount_to_invoice = 0.0
            for move_line in invoices_move_lines:
                currency = move_line.currency_id
                price_subtotal = currency._convert(move_line.price_subtotal, self.currency_id, self.company_id)
                # an analytic account can appear several time in an analytic distribution with different repartition percentage
                analytic_contribution = sum(
                    percentage for ids, percentage in move_line.analytic_distribution.items()
                    if str(self.analytic_account_id.id) in ids.split(',')
                ) / 100.
                if move_line.parent_state == 'draft':
                    if move_line.move_type == 'out_invoice':
                        amount_to_invoice += price_subtotal * analytic_contribution
                    else:  # move_line.move_type == 'out_refund'
                        amount_to_invoice -= price_subtotal * analytic_contribution
                else:  # move_line.parent_state == 'posted'
                    if move_line.move_type == 'out_invoice':
                        amount_invoiced += price_subtotal * analytic_contribution
                    else:  # moves_read['move_type'] == 'out_refund'
                        amount_invoiced -= price_subtotal * analytic_contribution
            # don't display the section if the final values are both 0 (invoice -> credit note)
            if amount_invoiced != 0 or amount_to_invoice != 0:
                section_id = 'other_invoice_revenues'
                invoices_revenues = {
                    'id': section_id,
                    'sequence': self._get_profitability_sequence_per_invoice_type()[section_id],
                    'invoiced': amount_invoiced,
                    'to_invoice': amount_to_invoice,
                }
                if with_action and (
                    self.env.user.has_group('sales_team.group_sale_salesman_all_leads')
                    or self.env.user.has_group('account.group_account_invoice')
                    or self.env.user.has_group('account.group_account_readonly')
                ):
                    invoices_revenues['action'] = self._get_action_for_profitability_section(invoices_move_lines.ids, section_id)
                return {
                    'data': [invoices_revenues],
                    'total': {
                        'invoiced': amount_invoiced,
                        'to_invoice': amount_to_invoice,
                    },
                }
        return {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}}

    def _add_invoice_items(self, domain, profitability_items, with_action=True):
        sale_lines = self.env['sale.order.line'].sudo()._read_group(
            self._get_profitability_sale_order_items_domain(domain),
            [],
            ['id:recordset'],
        )[0][0]
        revenue_items_from_invoices = self._get_revenues_items_from_invoices(
            excluded_move_line_ids=sale_lines.invoice_lines.ids,
            with_action=with_action
        )
        profitability_items['revenues']['data'] += revenue_items_from_invoices['data']
        profitability_items['revenues']['total']['to_invoice'] += revenue_items_from_invoices['total']['to_invoice']
        profitability_items['revenues']['total']['invoiced'] += revenue_items_from_invoices['total']['invoiced']

    def _get_profitability_items(self, with_action=True):
        profitability_items = super()._get_profitability_items(with_action)
        sale_items = self.sudo()._get_sale_order_items()
        domain = [
            ('order_id', 'in', sale_items.order_id.ids),
            '|',
                '|',
                    ('project_id', 'in', self.ids),
                    ('project_id', '=', False),
                ('id', 'in', sale_items.ids),
        ]
        revenue_items_from_sol = self._get_revenues_items_from_sol(
            domain,
            with_action,
        )
        profitability_items['revenues']['data'] += revenue_items_from_sol['data']
        profitability_items['revenues']['total']['to_invoice'] += revenue_items_from_sol['total']['to_invoice']
        profitability_items['revenues']['total']['invoiced'] += revenue_items_from_sol['total']['invoiced']
        self._add_invoice_items(domain, profitability_items, with_action=with_action)
        self._add_purchase_items(profitability_items, with_action=with_action)
        return profitability_items

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            self_sudo = self.sudo()
            buttons.append({
                'icon': 'dollar',
                'text': _lt('Sales Orders'),
                'number': self_sudo.sale_order_count,
                'action_type': 'object',
                'action': 'action_view_sos',
                'show': self_sudo.display_sales_stat_buttons and self_sudo.sale_order_count > 0,
                'sequence': 27,
            })
        if self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            buttons.append({
                'icon': 'dollar',
                'text': _lt('Sales Order Items'),
                'number': self.sale_order_line_count,
                'action_type': 'object',
                'action': 'action_view_sols',
                'show': self.display_sales_stat_buttons,
                'sequence': 28,
            })
        if self.env.user.has_group('account.group_account_readonly'):
            self_sudo = self.sudo()
            buttons.append({
                'icon': 'pencil-square-o',
                'text': _lt('Invoices'),
                'number': self_sudo.invoice_count,
                'action_type': 'object',
                'action': 'action_open_project_invoices',
                'show': bool(self.analytic_account_id) and self_sudo.invoice_count > 0,
                'sequence': 30,
            })
        if self.env.user.has_group('account.group_account_readonly'):
            self_sudo = self.sudo()
            buttons.append({
                'icon': 'pencil-square-o',
                'text': _lt('Vendor Bills'),
                'number': self_sudo.vendor_bill_count,
                'action_type': 'object',
                'action': 'action_open_project_vendor_bills',
                'show': self_sudo.vendor_bill_count > 0,
                'sequence': 38,
            })
        return buttons

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    def _get_hide_partner(self):
        return not self.allow_billable

    def _get_projects_to_make_billable_domain(self):
        return expression.AND([
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
        return action

    def action_open_project_vendor_bills(self):
        move_lines = self.env['account.move.line'].search_fetch(
            [
                ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                ('analytic_distribution', 'in', self.analytic_account_id.ids),
            ],
            ['move_id'],
        )
        vendor_bill_ids = move_lines.move_id.ids
        action_window = {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': [('id', 'in', vendor_bill_ids)],
            'context': {
                'create': False,
            }
        }
        if len(vendor_bill_ids) == 1:
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = vendor_bill_ids[0]
        return action_window
