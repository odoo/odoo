# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateSalesOrder(models.TransientModel):
    _name = 'project.create.sale.order'
    _description = "Create SO from project"

    @api.model
    def default_get(self, fields):
        result = super(ProjectCreateSalesOrder, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'project.project':
            raise UserError(_("You can only apply this action from a project."))

        active_id = self._context.get('active_id')
        if 'project_id' in fields and active_id:
            project = self.env['project.project'].browse(active_id)
            if project.sale_order_id:
                raise UserError(_("The project has already a sale order."))
            result['project_id'] = active_id
            if not result.get('partner_id', False):
                result['partner_id'] = project.partner_id.id
            if project.pricing_type != 'task_rate' and not result.get('line_ids', False):
                if project.pricing_type == 'employee_rate':
                    default_product = self.env.ref('sale_timesheet.time_product', False)
                    result['line_ids'] = [
                        (0, 0, {
                            'employee_id': e.employee_id.id,
                            'product_id': e.timesheet_product_id.id or default_product.id,
                            'price_unit': e.price_unit if e.timesheet_product_id else default_product.lst_price
                        }) for e in project.sale_line_employee_ids]
                    employee_from_timesheet = project.task_ids.timesheet_ids.employee_id - project.sale_line_employee_ids.employee_id
                    result['line_ids'] += [
                        (0, 0, {
                            'employee_id': e.id,
                            'product_id': default_product.id,
                            'price_unit': default_product.lst_price
                        }) for e in employee_from_timesheet]
        return result

    project_id = fields.Many2one('project.project', "Project", domain=[('sale_line_id', '=', False)], help="Project for which we are creating a sales order", required=True)
    company_id = fields.Many2one(related='project_id.company_id')
    partner_id = fields.Many2one('res.partner', string="Customer", required=True, help="Customer of the sales order")
    commercial_partner_id = fields.Many2one(related='partner_id.commercial_partner_id')

    sale_order_id = fields.Many2one(
        'sale.order', string="Sales Order",
        domain="['|', '|', ('partner_id', '=', partner_id), ('partner_id', 'child_of', commercial_partner_id), ('partner_id', 'parent_of', partner_id)]")

    line_ids = fields.One2many('project.create.sale.order.line', 'wizard_id', string='Lines')
    info_invoice = fields.Char(compute='_compute_info_invoice')

    @api.depends('sale_order_id')
    def _compute_info_invoice(self):
        for line in self:
            domain = self.env['sale.order.line']._timesheet_compute_delivered_quantity_domain()
            timesheet = self.env['account.analytic.line']._read_group(domain + [('task_id', 'in', line.project_id.tasks.ids), ('so_line', '=', False), ('timesheet_invoice_id', '=', False)], aggregates=['unit_amount:sum'])
            [unit_amount] = timesheet[0]
            if not unit_amount:
                line.info_invoice = False
                continue
            company_uom = self.env.company.timesheet_encode_uom_id
            label = _("hours")
            if company_uom == self.env.ref('uom.product_uom_day'):
                label = _("days")
            line.info_invoice = _("%(amount)s %(label)s will be added to the new Sales Order.", amount=round(unit_amount, 2), label=label)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.sale_order_id = False

    def action_create_sale_order(self):
        # if project linked to SO line or at least on tasks with SO line, then we consider project as billable.
        if self.project_id.sale_line_id:
            raise UserError(_("The project is already linked to a sales order item."))
        # at least one line
        if not self.line_ids:
            raise UserError(_("At least one line should be filled."))

        if self.line_ids.employee_id:
            # all employee having timesheet should be in the wizard map
            timesheet_employees = self.env['account.analytic.line'].search([('task_id', 'in', self.project_id.tasks.ids)]).mapped('employee_id')
            map_employees = self.line_ids.mapped('employee_id')
            missing_meployees = timesheet_employees - map_employees
            if missing_meployees:
                raise UserError(_('The Sales Order cannot be created because you did not enter some employees that entered timesheets on this project. Please list all the relevant employees before creating the Sales Order.\nMissing employee(s): %s', ', '.join(missing_meployees.mapped('name'))))

        # check here if timesheet already linked to SO line
        timesheet_with_so_line = self.env['account.analytic.line'].search_count([('task_id', 'in', self.project_id.tasks.ids), ('so_line', '!=', False)], limit=1)
        if timesheet_with_so_line:
            raise UserError(_('The sales order cannot be created because some timesheets of this project are already linked to another sales order.'))

        # create SO according to the chosen billable type
        sale_order = self._create_sale_order()

        view_form_id = self.env.ref('sale.view_order_form').id
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action.update({
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': sale_order.name,
            'res_id': sale_order.id,
        })
        return action

    def _create_sale_order(self):
        """ Private implementation of generating the sales order """
        sale_order = self.env['sale.order'].create({
            'project_id': self.project_id.id,
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.project_id.analytic_account_id.id,
            'client_order_ref': self.project_id.name,
            'company_id': self.project_id.company_id.id or self.env.company.id,
        })
        # rewrite the user as the onchange_partner_id erases it
        sale_order.write({'user_id': self.project_id.user_id.id})

        # create the sale lines, the map (optional), and assign existing timesheet to sale lines
        self._make_billable(sale_order)

        # confirm SO
        if sale_order.state != 'sale':
            sale_order.action_confirm()
        return sale_order

    def _make_billable(self, sale_order):
        if not self.line_ids.employee_id:  # Then we configure the project with pricing type is equal to project rate
            self._make_billable_at_project_rate(sale_order)
        else:  # Then we configure the project with pricing type is equal to employee rate
            self._make_billable_at_employee_rate(sale_order)

    def _make_billable_at_project_rate(self, sale_order):
        self.ensure_one()
        task_left = self.project_id.tasks.filtered(lambda task: not task.sale_line_id)
        for wizard_line in self.line_ids:
            task_ids = self.project_id.tasks.filtered(lambda task: not task.sale_line_id and task.timesheet_product_id == wizard_line.product_id)
            task_left -= task_ids
            # trying to simulate the SO line created a task, according to the product configuration
            # To avoid, generating a task when confirming the SO
            task_id = False
            if task_ids and wizard_line.product_id.service_tracking in ['task_in_project', 'task_global_project']:
                task_id = task_ids.ids[0]

            # create SO line
            sale_order_line = self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': wizard_line.product_id.id,
                'price_unit': wizard_line.price_unit,
                'project_id': self.project_id.id,  # prevent to re-create a project on confirmation
                'task_id': task_id,
                'product_uom_qty': 0.0,
            })

            # link the tasks to the SO line
            task_ids.write({
                'sale_line_id': sale_order_line.id,
                'partner_id': sale_order.partner_id.id,
            })

            # assign SOL to timesheets
            search_domain = [('task_id', 'in', task_ids.ids), ('so_line', '=', False)]
            self.env['account.analytic.line'].search(search_domain).write({
                'so_line': sale_order_line.id
            })
            sale_order_line.with_context({'no_update_allocated_hours': True}).write({
                'product_uom_qty': sale_order_line.qty_delivered
            })
            # Avoid recomputing price_unit
            self.env.remove_to_compute(self.env['sale.order.line']._fields['price_unit'], sale_order_line)

        self.project_id.write({
            'sale_order_id': sale_order.id,
            'sale_line_id': sale_order_line.id,  # we take the last sale_order_line created
            'partner_id': self.partner_id.id,
        })

        if task_left:
            task_left.sale_line_id = False

    def _make_billable_at_employee_rate(self, sale_order):
        # trying to simulate the SO line created a task, according to the product configuration
        # To avoid, generating a task when confirming the SO
        task_id = self.env['project.task'].search([('project_id', '=', self.project_id.id)], order='create_date DESC', limit=1).id
        project_id = self.project_id.id

        lines_already_present = dict([(l.employee_id.id, l) for l in self.project_id.sale_line_employee_ids])

        non_billable_tasks = self.project_id.tasks.filtered(lambda task: not task.sale_line_id)

        map_entries = self.env['project.sale.line.employee.map']
        EmployeeMap = self.env['project.sale.line.employee.map'].sudo()

        # create SO lines: create on SOL per product/price. So many employee can be linked to the same SOL
        map_product_price_sol = {}  # (product_id, price) --> SOL
        for wizard_line in self.line_ids:
            map_key = (wizard_line.product_id.id, wizard_line.price_unit)
            if map_key not in map_product_price_sol:
                values = {
                    'order_id': sale_order.id,
                    'product_id': wizard_line.product_id.id,
                    'price_unit': wizard_line.price_unit,
                    'product_uom_qty': 0.0,
                }
                if wizard_line.product_id.service_tracking in ['task_in_project', 'task_global_project']:
                    values['task_id'] = task_id
                if wizard_line.product_id.service_tracking in ['task_in_project', 'project_only']:
                    values['project_id'] = project_id

                sale_order_line = self.env['sale.order.line'].create(values)
                map_product_price_sol[map_key] = sale_order_line

            if wizard_line.employee_id.id not in lines_already_present:
                map_entries |= EmployeeMap.create({
                    'project_id': self.project_id.id,
                    'sale_line_id': map_product_price_sol[map_key].id,
                    'employee_id': wizard_line.employee_id.id,
                })
            else:
                map_entries |= lines_already_present[wizard_line.employee_id.id]
                lines_already_present[wizard_line.employee_id.id].write({
                    'sale_line_id': map_product_price_sol[map_key].id
                })

        # link the project to the SO
        self.project_id.write({
            'sale_order_id': sale_order.id,
            'sale_line_id': sale_order.order_line[0].id,
            'partner_id': self.partner_id.id,
        })
        non_billable_tasks.write({
            'partner_id': sale_order.partner_id.id,
        })

        # assign SOL to timesheets
        for map_entry in map_entries:
            search_domain = [('employee_id', '=', map_entry.employee_id.id), ('so_line', '=', False), ('task_id', 'in', self.project_id.tasks.ids)]
            self.env['account.analytic.line'].search(search_domain).write({
                'so_line': map_entry.sale_line_id.id
            })
            map_entry.sale_line_id.with_context({'no_update_allocated_hours': True}).write({
                'product_uom_qty': map_entry.sale_line_id.qty_delivered,
            })
            # Avoid recomputing price_unit
            self.env.remove_to_compute(self.env['sale.order.line']._fields['price_unit'], map_entry.sale_line_id)
        return map_entries


class ProjectCreateSalesOrderLine(models.TransientModel):
    _name = 'project.create.sale.order.line'
    _description = 'Create SO Line from project'
    _order = 'id,create_date'

    wizard_id = fields.Many2one('project.create.sale.order', required=True)
    product_id = fields.Many2one('product.product', domain=[('detailed_type', '=', 'service'), ('invoice_policy', '=', 'delivery'), ('service_type', '=', 'timesheet')], string="Service",
        help="Product of the sales order item. Must be a service invoiced based on timesheets on tasks.")
    price_unit = fields.Float("Unit Price", help="Unit price of the sales order item.")
    currency_id = fields.Many2one('res.currency', string="Currency")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee that has timesheets on the project.")

    _sql_constraints = [
        ('unique_employee_per_wizard', 'UNIQUE(wizard_id, employee_id)', "An employee cannot be selected more than once in the mapping. Please remove duplicate(s) and try again."),
    ]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.price_unit = self.product_id.lst_price or 0
        self.currency_id = self.product_id.currency_id
