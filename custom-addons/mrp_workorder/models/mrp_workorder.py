# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime
from pytz import utc

from odoo import Command, api, fields, models, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, relativedelta
from odoo.addons.resource.models.utils import Intervals, sum_intervals, string_to_datetime
from odoo.http import request


class MrpProductionWorkcenterLine(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    quality_point_ids = fields.Many2many('quality.point', compute='_compute_quality_point_ids', store=True)
    quality_point_count = fields.Integer('Steps', compute='_compute_quality_point_count')

    check_ids = fields.One2many('quality.check', 'workorder_id')
    finished_product_check_ids = fields.Many2many('quality.check', compute='_compute_finished_product_check_ids')
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', 'workorder_id')
    quality_alert_count = fields.Integer(compute="_compute_quality_alert_count")

    current_quality_check_id = fields.Many2one(
        'quality.check', "Current Quality Check", check_company=True)

    # QC-related fields
    allow_producing_quantity_change = fields.Boolean('Allow Changes to Producing Quantity', default=True)

    is_last_lot = fields.Boolean('Is Last lot', compute='_compute_is_last_lot')
    is_first_started_wo = fields.Boolean('Is The first Work Order', compute='_compute_is_last_unfinished_wo')
    is_last_unfinished_wo = fields.Boolean('Is Last Work Order To Process', compute='_compute_is_last_unfinished_wo', store=False)
    lot_id = fields.Many2one(related='current_quality_check_id.lot_id', readonly=False)
    move_id = fields.Many2one(related='current_quality_check_id.move_id', readonly=False)
    move_line_id = fields.Many2one(related='current_quality_check_id.move_line_id', readonly=False)
    move_line_ids = fields.One2many(related='move_id.move_line_ids')
    quality_state = fields.Selection(related='current_quality_check_id.quality_state', string="Quality State", readonly=False)
    qty_done = fields.Float(related='current_quality_check_id.qty_done', readonly=False)
    test_type_id = fields.Many2one('quality.point.test_type', 'Test Type', related='current_quality_check_id.test_type_id')
    test_type = fields.Char(related='test_type_id.technical_name')
    user_id = fields.Many2one(related='current_quality_check_id.user_id', readonly=False)
    worksheet_page = fields.Integer('Worksheet page')
    picture = fields.Binary(related='current_quality_check_id.picture', readonly=False)
    additional = fields.Boolean(related='current_quality_check_id.additional')

    # used to display the connected employee that will start a workorder on the tablet view
    employee_id = fields.Many2one('hr.employee', string="Employee", compute='_compute_employee_id')
    employee_name = fields.Char(compute='_compute_employee_id')

    # employees that started working on the wo
    employee_ids = fields.Many2many('hr.employee', string='Working employees', copy=False)
    # employees assigned to the wo
    employee_assigned_ids = fields.Many2many('hr.employee', 'mrp_workorder_employee_assigned',
                                             'workorder_id', 'employee_id', string='Assigned', copy=False)
    # employees connected
    connected_employee_ids = fields.Many2many('hr.employee', search='search_is_assigned_to_connected', store=False)

    # list of employees allowed to work on the workcenter
    allowed_employees = fields.Many2many(related='workcenter_id.employee_ids')
    # True if all employees are allowed on that workcenter
    all_employees_allowed = fields.Boolean(compute='_all_employees_allowed')

    @api.depends('operation_id')
    def _compute_quality_point_ids(self):
        for workorder in self:
            quality_points = workorder.operation_id.quality_point_ids
            quality_points = quality_points.filtered(lambda qp: (not qp.product_ids or workorder.production_id.product_id in qp.product_ids) and (qp.company_id == workorder.company_id))
            workorder.quality_point_ids = quality_points

    @api.depends('operation_id')
    def _compute_quality_point_count(self):
        for workorder in self:
            quality_point = workorder.operation_id.quality_point_ids
            workorder.quality_point_count = len(quality_point)

    @api.depends('qty_producing', 'qty_remaining')
    def _compute_is_last_lot(self):
        for wo in self:
            precision = wo.production_id.product_uom_id.rounding
            wo.is_last_lot = float_compare(wo.qty_producing, wo.qty_remaining, precision_rounding=precision) >= 0

    @api.depends('production_id.workorder_ids')
    def _compute_is_last_unfinished_wo(self):
        for wo in self:
            wo.is_first_started_wo = all(wo.state != 'done' for wo in (wo.production_id.workorder_ids - wo))
            other_wos = wo.production_id.workorder_ids - wo
            other_states = other_wos.mapped(lambda w: w.state in ['done', 'cancel'])
            wo.is_last_unfinished_wo = all(other_states)

    @api.depends('check_ids')
    def _compute_finished_product_check_ids(self):
        for wo in self:
            wo.finished_product_check_ids = wo.check_ids.filtered(lambda c: c.finished_product_sequence == wo.qty_produced)

    def write(self, values):
        res = super().write(values)
        if 'qty_producing' in values:
            for wo in self:
                for check in wo.check_ids:
                    if check.component_id:
                        check._update_component_quantity()
        return res

    def unlink(self):
        self.check_ids.sudo().unlink()
        return super().unlink()

    def action_back(self):
        self.ensure_one()
        if self._should_be_pending():
            self.button_pending()
        domain = [('state', 'not in', ['done', 'cancel', 'pending'])]
        if self.env.context.get('from_manufacturing_order'):
            # from workorder on MO
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            action['domain'] = domain
            action['context'] = {
                'no_breadcrumbs': True,
                'search_default_production_id': self.production_id.id,
                'from_manufacturing_order': True,
            }
        elif self.env.context.get('from_production_order'):
            # from workorder list view
            action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_workorder_todo")
            action['target'] = 'main'
            action['context'] = dict(literal_eval(action['context']), no_breadcrumbs=True)
        else:
            # from workcenter kanban view
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            action['domain'] = domain
            action['context'] = {
                'no_breadcrumbs': True,
                'search_default_workcenter_id': self.workcenter_id.id,
                'search_default_ready': True,
                'search_default_progress': True,
            }
        if self.employee_id:
            action['context']['employee_id'] = self.employee_id.id
            action['context']['employee_name'] = self.employee_id.name
        if self.employee_ids:
            action['context']['employee_ids'] = self.employee_ids
        return clean_action(action, self.env)

    def action_cancel(self):
        self.mapped('check_ids').filtered(lambda c: c.quality_state == 'none').sudo().unlink()
        return super(MrpProductionWorkcenterLine, self).action_cancel()

    def action_generate_serial(self):
        self.ensure_one()
        self.finished_lot_id = self.env['stock.lot'].create(
            self.production_id._prepare_stock_lot_values()
        )

    def _create_subsequent_checks(self):
        """ When processing a step with regiter a consumed material
        that's a lot we will some times need to create a new
        intermediate check.
        e.g.: Register 2 product A tracked by SN. We will register one
        with the current checks but we need to generate a second step
        for the second SN. Same for lot if the user wants to use more
        than one lot.
        """
        # Create another quality check if necessary
        next_check = self.current_quality_check_id.next_check_id
        if next_check.component_id != self.current_quality_check_id.product_id or\
                next_check.point_id != self.current_quality_check_id.point_id:
            # TODO: manage reservation here

            # Creating quality checks
            quality_check_data = {
                'workorder_id': self.id,
                'production_id': self.production_id.id,
                'product_id': self.product_id.id,
                'company_id': self.company_id.id,
                'finished_product_sequence': self.qty_produced,
            }
            if self.current_quality_check_id.point_id:
                quality_check_data.update({
                    'point_id': self.current_quality_check_id.point_id.id,
                    'team_id': self.current_quality_check_id.point_id.team_id.id,
                })
            else:
                quality_check_data.update({
                    'component_id': self.current_quality_check_id.component_id.id,
                    'test_type_id': self.current_quality_check_id.test_type_id.id,
                    'team_id': self.current_quality_check_id.team_id.id,
                })
            move = self.current_quality_check_id.move_id
            quality_check_data.update(self._defaults_from_move(move))
            new_check = self.env['quality.check'].create(quality_check_data)
            new_check._insert_in_chain('after', self.current_quality_check_id)

    def _change_quality_check(self, position):
        """Change the quality check currently set on the workorder `self`.

        The workorder points to a check. A check belongs to a chain.
        This method allows to change the selected check by moving on the checks
        chain according to `position`.

        :param position: Where we need to change the cursor on the check chain
        :type position: string
        """
        self.ensure_one()
        assert position in ['first', 'next', 'previous', 'last']
        checks_to_consider = self.check_ids.filtered(lambda c: c.quality_state == 'none')
        if position == 'first':
            check = checks_to_consider.filtered(lambda check: not check.previous_check_id)
        elif position == 'next':
            check = self.current_quality_check_id.next_check_id
            if not check:
                check = checks_to_consider[:1]
            elif check.quality_state != 'none':
                self.current_quality_check_id = check
                return self._change_quality_check(position='next')
            if check.test_type in ('register_byproducts', 'register_consumed_materials'):
                check._update_component_quantity()
        elif position == 'previous':
            check = self.current_quality_check_id.previous_check_id
        else:
            check = checks_to_consider.filtered(lambda check: not check.next_check_id)
        self.write({
            'allow_producing_quantity_change':
                not check.previous_check_id.filtered(lambda c: c.quality_state != 'fail')
                and all(c.quality_state != 'fail' for c in checks_to_consider)
                and self.is_first_started_wo,
            'current_quality_check_id': check.id,
            'worksheet_page': check.point_id.worksheet_page,
        })

    def action_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet_menu').id, 'form']],
            'name': _('Menu'),
            'target': 'new',
            'res_id': self.id,
        }

    def action_add_component(self):
        action = self.production_id.action_add_component()
        action['context']['default_workorder_id'] = self.id
        return action

    def action_add_byproduct(self):
        action = self.production_id.action_add_byproduct()
        action['context']['default_workorder_id'] = self.id
        return action

    def button_start(self, bypass=False):
        skip_employee_check = bypass or (not request and not self.env.user.employee_id)
        main_employee = False
        if not skip_employee_check:
            if not self.env.context.get('mrp_display'):
                main_employee = self.env.user.employee_id.id
                if not self.env.user.employee_id:
                    raise UserError(_("You need to link this user to an employee of this company to process the work order"))
            else:
                connected_employees = self.env['hr.employee'].get_employees_connected()
                if len(connected_employees) == 0:
                    raise UserError(_("You need to log in to process this work order."))
                main_employee = self.env['hr.employee'].get_session_owner()
                if not main_employee:
                    raise UserError(_("There is no session chief. Please log in."))
                if any(main_employee not in [emp.id for emp in wo.allowed_employees] and not wo.all_employees_allowed for wo in self):
                    raise UserError(_("You are not allowed to work on the workorder"))

        res = super().button_start()

        for wo in self:
            if len(wo.time_ids) == 1 or all(wo.time_ids.mapped('date_end')):
                for check in wo.check_ids:
                    if check.component_id:
                        check._update_component_quantity()

            if main_employee:
                if len(wo.allowed_employees) == 0 or main_employee in [emp.id for emp in wo.allowed_employees]:
                    wo.start_employee(self.env['hr.employee'].browse(main_employee).id)
                    wo.employee_ids |= self.env['hr.employee'].browse(main_employee)

        return res

    def button_finish(self):
        """ When using the Done button of the simplified view, validate directly some types of quality checks
        """
        self.verify_quality_checks()
        return super().button_finish()

    def verify_quality_checks(self):
        for check in self.check_ids:
            if check.quality_state in ['pass', 'fail']:
                continue
            if check.test_type in ['register_consumed_materials', 'register_byproducts', 'instructions']:
                check.quality_state = 'pass'
            else:
                raise UserError(_("You need to complete Quality Checks using the Shop Floor before marking Work Order as Done."))

    def action_propose_change(self, change_type, check_id):
        change_type_to_title = {'update_step': 'Update Instructions', 'remove_step': 'Remove Step', 'set_picture': 'Change Picture'}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propose.change',
            'views': [[self.env.ref('mrp_workorder.view_propose_change_wizard').id, 'form']],
            'name': change_type_to_title[change_type],
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_step_id': check_id,
                'default_change_type': change_type,
            }
        }

    def action_add_step(self):
        self.ensure_one()
        if self.current_quality_check_id:
            team = self.current_quality_check_id.team_id
        else:
            team = self.env['quality.alert.team'].search(['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'views': [[self.env.ref('mrp_workorder.add_quality_check_from_tablet').id, 'form']],
            'name': _('Add a Step'),
            'target': 'new',
            'context': {
                'default_test_type_id': self.env.ref('quality.test_type_instructions').id,
                'default_workorder_id': self.id,
                'default_production_id': self.production_id.id,
                'default_product_id': self.product_id.id,
                'default_team_id': team.id,
            }
        }

    def action_open_mes(self):
        action = self.env['ir.actions.actions']._for_xml_id('mrp_workorder.action_mrp_display')
        action['context'] = {
            'workcenter_id': self.workcenter_id.id,
            'search_default_name': self.production_id.name,
            'shouldHideNewWorkcenterButton': True,
        }
        return action

    def _compute_check(self):
        for workorder in self:
            todo = False
            fail = False
            for check in workorder.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            workorder.quality_check_fail = fail
            workorder.quality_check_todo = todo

    def _compute_quality_alert_count(self):
        for workorder in self:
            workorder.quality_alert_count = len(workorder.quality_alert_ids)

    def _create_checks(self):
        for wo in self:
            # Track components which have a control point
            processed_move = self.env['stock.move']

            production = wo.production_id

            move_raw_ids = wo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            move_finished_ids = wo.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id != wo.production_id.product_id)
            previous_check = self.env['quality.check']
            for point in wo.quality_point_ids:
                # Check if we need a quality control for this point
                if point.check_execute_now():
                    moves = self.env['stock.move']
                    values = {
                        'production_id': production.id,
                        'workorder_id': wo.id,
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'company_id': wo.company_id.id,
                        'product_id': production.product_id.id,
                        # Two steps are from the same production
                        # if and only if the produced quantities at the time they were created are equal.
                        'finished_product_sequence': wo.qty_produced,
                        'previous_check_id': previous_check.id,
                        'worksheet_document': point.worksheet_document,
                    }
                    if point.test_type == 'register_byproducts':
                        moves = move_finished_ids.filtered(lambda m: m.product_id == point.component_id)
                        if not moves:
                            moves = production.move_finished_ids.filtered(lambda m: not m.operation_id and m.product_id == point.component_id)
                    elif point.test_type == 'register_consumed_materials':
                        moves = move_raw_ids.filtered(lambda m: m.product_id == point.component_id)
                        if not moves:
                            moves = production.move_raw_ids.filtered(lambda m: not m.operation_id and m.product_id == point.component_id)
                    else:
                        check = self.env['quality.check'].create(values)
                        previous_check.next_check_id = check
                        previous_check = check
                    # Create 'register ...' checks
                    for move in moves:
                        check_vals = values.copy()
                        check_vals.update(wo._defaults_from_move(move))
                        # Create quality check and link it to the chain
                        check_vals.update({'previous_check_id': previous_check.id})
                        check = self.env['quality.check'].create(check_vals)
                        previous_check.next_check_id = check
                        previous_check = check
                    processed_move |= moves

            # Set default quality_check
            wo._change_quality_check(position='first')

    def _get_byproduct_move_to_update(self):
        moves = super(MrpProductionWorkcenterLine, self)._get_byproduct_move_to_update()
        return moves.filtered(lambda m: m.product_id.tracking == 'none')

    def pre_record_production(self):
        self.ensure_one()
        self._check_company()
        if any(x.quality_state == 'none' for x in self.check_ids if x.test_type != 'instructions'):
            raise UserError(_('You still need to do the quality checks!'))
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

    def record_production(self):
        if not self:
            return True

        self.pre_record_production()

        backorder = False
        # Trigger the backorder process if we produce less than expected
        if float_compare(self.qty_producing, self.qty_remaining, precision_rounding=self.product_uom_id.rounding) == -1 and self.is_first_started_wo:
            backorder = self.production_id._split_productions()[1:]
            for workorder in backorder.workorder_ids:
                if workorder.product_tracking == 'serial':
                    workorder.qty_producing = 1
                elif not self.env.context.get('no_start_next', False):
                    workorder.qty_producing = workorder.qty_remaining
            self.production_id.product_qty = self.qty_producing
        else:
            if self.operation_id:
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: p.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id).state not in ('cancel', 'done')
                )[:1]
            else:
                index = list(self.production_id.workorder_ids).index(self)
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: index < len(p.workorder_ids) and p.workorder_ids[index].state not in ('cancel', 'done')
                )[:1]

        self.move_raw_ids.picked = True
        self.production_id.move_byproduct_ids.filtered(lambda m: m.operation_id == self.operation_id).picked = True
        self.button_finish()

        if backorder:
            for wo in (self.production_id | backorder).workorder_ids:
                if wo.state in ('done', 'cancel'):
                    continue
                if not wo.current_quality_check_id or not wo.current_quality_check_id.move_line_id:
                    wo.current_quality_check_id.update(wo._defaults_from_move(wo.move_id))
                if wo.move_id:
                    wo.current_quality_check_id._update_component_quantity()
            if not self.env.context.get('no_start_next'):
                next_wo = self.env['mrp.workorder']
                if self.operation_id:
                    next_wo = backorder.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id and wo.state in ('ready', 'progress'))
                else:
                    index = list(self.production_id.workorder_ids).index(self)
                    if backorder.workorder_ids[index].state in ('ready', 'progress'):
                        next_wo = backorder.workorder_ids[index]
                if next_wo:
                    action = next_wo.open_tablet_view()
                    if self.employee_id:
                        action['context']['employee_id'] = self.employee_id.id
                    return action
        return self.action_back()

    def _defaults_from_move(self, move):
        self.ensure_one()
        vals = {'move_id': move.id}
        move_line_id = move.move_line_ids.filtered(lambda sml: sml._without_quality_checks())[:1]
        if move_line_id:
            vals.update({
                'move_line_id': move_line_id.id,
                'qty_done': move_line_id.quantity or 1.0
            })
            if move.picking_type_id.prefill_lot_tablet:
                vals['lot_id'] = move_line_id.lot_id.id
        return vals

    # --------------------------
    # Buttons from quality.check
    # --------------------------

    def open_tablet_view(self):
        self.ensure_one()
        self.env['hr.employee'].login_user_employee()
        if self._should_start():
            self.button_start()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.tablet_client_action")
        action['target'] = 'fullscreen'
        action['res_id'] = self.id
        action['context'] = {
            'active_id': self.id,
            'from_production_order': self.env.context.get('from_production_order'),
            'from_manufacturing_order': self.env.context.get('from_manufacturing_order')
        }
        return action

    def action_open_manufacturing_order(self):
        no_start_next = self.env.context.get("no_start_next", True)
        action = self.with_context(no_start_next=no_start_next).do_finish()
        try:
            with self.env.cr.savepoint():
                res = self.production_id.button_mark_done()
                if res is not True:
                    res['context'] = dict(res.get('context', {}), from_workorder=True)
                    return res
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.production_id.activity_schedule(
                'mail.mail_activity_data_warning',
                note=str(e),
                summary=('The %s could not be closed') % (self.production_id.name),
                user_id=self.env.user.id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action

    def do_finish(self):
        self.end_all()
        if self.state != 'done':
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')], limit=1)
            if len(loss_id) < 1:
                raise UserError(_("You need to define at least one productivity loss in the category 'Productive'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
            action = self.record_production()
            self._set_default_time_log(loss_id)
            if action is not True:
                return action
        # workorder tree view action should redirect to the same view instead of workorder kanban view when WO mark as done.
        return self.action_back()

    def get_workorder_data(self):
        # order quality check chain
        ele = self.check_ids.filtered(lambda check: not check.previous_check_id)
        sorted_check_list = []
        while ele:
            sorted_check_list += ele.ids
            ele = ele.next_check_id
        data = {
            'mrp.workorder': self.read(self._get_fields_for_tablet(), load=False)[0],
            'quality.check': self.check_ids._get_fields_for_tablet(sorted_check_list),
            'operation': self.operation_id.read(self.operation_id._get_fields_for_tablet())[0] if self.operation_id else {},
            'working_state': self.workcenter_id.working_state,
            'has_bom': bool(self.production_id.bom_id),
            'views': {
                'workorder': self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id,
                'check': self.env.ref('mrp_workorder.quality_check_view_form_tablet').id,
            },
        }
        employee_domain = [('company_id', '=', self.company_id.id)]
        if self.workcenter_id.employee_ids:
            employee_domain = [('id', 'in', self.workcenter_id.employee_ids.ids)]
        fields_to_read = self.env['hr.employee']._get_employee_fields_for_tablet()
        working_state = self.working_state
        data.update({
            "working_state": working_state,
            "employee_id": self.employee_id.id,
            "employee_ids": self.employee_ids.ids,
            "employee_list": self.env['hr.employee'].search_read(employee_domain, fields_to_read, load=False),
        })
        return data

    def get_summary_data(self):
        self.ensure_one()
        # show rainbow man only the first time
        show_rainbow = any(not t.date_end for t in self.time_ids)
        self.end_all()
        if any(step.quality_state == 'none' for step in self.check_ids):
            raise UserError(_('You still need to do the quality checks!'))
        last30op = self.env['mrp.workorder'].search_read([
            ('operation_id', '=', self.operation_id.id),
            ('state', '=', 'done'),
            ('date_finished', '>', fields.datetime.today() - relativedelta(days=30)),
        ], ['duration', 'qty_produced'])
        last30op = sorted([item['duration'] / item['qty_produced'] for item in last30op])
        # show rainbow man only for the best time in the last 30 days.
        if last30op:
            show_rainbow = show_rainbow and float_compare((self.duration / self.qty_producing), last30op[0], precision_digits=2) <= 0

        score = 3
        if self.check_ids:
            passed_checks = len([check for check in self.check_ids if check.quality_state == 'pass'])
            score = int(3.0 * passed_checks / len(self.check_ids))

        return {
            'duration': self.duration,
            'position': bisect_left(last30op, self.duration), # which position regarded other workorders ranked by duration
            'quality_score': score,
            'show_rainbow': show_rainbow,
        }

    def _action_confirm(self):
        res = super()._action_confirm()
        self.filtered(lambda wo: wo.state != 'cancel' and not wo.check_ids)._create_checks()
        return res

    def _update_qty_producing(self, quantity):
        if float_is_zero(quantity, precision_rounding=self.product_uom_id.rounding):
            self.check_ids.unlink()
        super()._update_qty_producing(quantity)

    def _web_gantt_progress_bar_workcenter_id(self, res_ids, start, stop):
        self.env['mrp.workorder'].check_access_rights('read')
        workcenters = self.env['mrp.workcenter'].search([('id', 'in', res_ids)])
        workorders = self.env['mrp.workorder'].search([
            ('workcenter_id', 'in', res_ids),
            ('state', 'not in', ['done', 'cancel']),
            ('date_start', '<=', stop.replace(tzinfo=None)),
            ('date_finished', '>=', start.replace(tzinfo=None)),
        ])
        planned_hours = defaultdict(float)
        workcenters_work_intervals, dummy = workcenters.resource_id._get_valid_work_intervals(start, stop)
        for workorder in workorders:
            max_start = max(start, utc.localize(workorder.date_start))
            min_finished = min(stop, utc.localize(workorder.date_finished))
            interval = Intervals([(max_start, min_finished, self.env['resource.calendar.attendance'])])
            work_intervals = interval & workcenters_work_intervals[workorder.workcenter_id.resource_id.id]
            planned_hours[workorder.workcenter_id] += sum_intervals(work_intervals)
        work_hours = {
            id: sum_intervals(work_intervals) for id, work_intervals in workcenters_work_intervals.items()
        }
        return {
            workcenter.id: {
                'value': planned_hours[workcenter],
                'max_value': work_hours.get(workcenter.resource_id.id, 0.0),
            }
            for workcenter in workcenters
        }

    def _web_gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'workcenter_id':
            return dict(
                self._web_gantt_progress_bar_workcenter_id(res_ids, start, stop),
                warning=_("This workcenter isn't expected to have open workorders during this period. Work hours :"),
            )
        raise NotImplementedError("This Progress Bar is not implemented.")

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)
        today = datetime.now(utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = max(start_utc, today)
        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._web_gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)
        return progress_bars

    def _get_fields_for_tablet(self):
        """ List of fields on the workorder object that are needed by the tablet
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        return [
            'production_id',
            'name',
            'qty_producing',
            'state',
            'company_id',
            'workcenter_id',
            'current_quality_check_id',
            'operation_note',
        ]

    def _should_be_pending(self):
        return self.is_user_working and self.working_state != 'blocked' and len(self.employee_ids.ids) == 0

    def _should_start(self):
        if self.working_state != 'blocked' and self.state in ('ready', 'waiting', 'progress', 'pending'):
            if self.env['hr.employee'].get_session_owner():
                return True
            else:
                self.button_start(bypass=True)
        return False

    def _compute_duration(self):
        wo_ids_without_employees = set()
        for wo in self:
            wo.duration = wo.get_duration()
            wo.duration_unit = round(wo.duration / max(wo.qty_produced, 1), 2)
            if wo.duration_expected:
                wo.duration_percent = max(-2147483648, min(2147483647, 100 * (wo.duration_expected - wo.duration) / wo.duration_expected))
            else:
                wo.duration_percent = 0
        return super(MrpProductionWorkcenterLine, self.env['mrp.workorder'].browse(wo_ids_without_employees))._compute_duration()

    @api.depends('employee_ids')
    def _compute_employee_id(self):
        main_employee_connected = self.env['hr.employee'].get_session_owner()
        self.employee_id = main_employee_connected
        self.employee_name = self.env['hr.employee'].browse(main_employee_connected).name

    def search_is_assigned_to_connected(self, operator, value):
        # retrieving employees connected in the session
        main_employee_connected = self.env['hr.employee'].get_session_owner()
        # if no one is connected, all records are valid
        if not main_employee_connected:
            return []
        search_query = self.env['mrp.workorder']._search([('employee_assigned_ids', '=', main_employee_connected)])
        return [('id', operator, search_query)]

    @api.depends('all_employees_allowed')
    def _all_employees_allowed(self):
        for wo in self:
            wo.all_employees_allowed = len(wo.allowed_employees) == 0

    def start_employee(self, employee_id):
        self.ensure_one()
        if employee_id in self.employee_ids.ids and any(not t.date_end for t in self.time_ids if t.employee_id.id == employee_id):
            return
        self.employee_ids = [Command.link(employee_id)]
        time_data = self._prepare_timeline_vals(self.duration, fields.Datetime.now())
        time_data['employee_id'] = employee_id
        self.env['mrp.workcenter.productivity'].create(time_data)
        self.state = "progress"

    def stop_employee(self, employee_ids):
        self.employee_ids = [Command.unlink(emp) for emp in employee_ids]
        self.env['mrp.workcenter.productivity'].search([
            ('employee_id', 'in', employee_ids),
            ('workorder_id', 'in', self.ids),
            ('date_end', '=', False)
        ])._close()

    def _should_start_timer(self):
        """ Return True if the timer should start once the workorder is opened."""
        self.ensure_one()
        return False

    def _intervals_duration(self, intervals):
        """ Return the duration of the given intervals.
        If intervals overlaps the duration is only counted once.

        The timer could be share between several intervals. However it is not
        an issue since the purpose is to make a difference between employee time and
        blocking time.

        :param list intervals: list of tuple (date_start, date_end, timer)
        """
        if not intervals:
            return 0.0
        duration = 0
        for date_start, date_stop, timer in Intervals(intervals):
            duration += timer.loss_id._convert_to_duration(date_start, date_stop, timer.workcenter_id)
        return duration

    def get_duration(self):
        self.ensure_one()
        now = fields.Datetime.now()
        loss_type_times = defaultdict(lambda: self.env['mrp.workcenter.productivity'])
        for time in self.time_ids:
            loss_type_times[time.loss_id.loss_type] |= time
        duration = 0
        for dummy, times in loss_type_times.items():
            duration += self._intervals_duration([(t.date_start, t.date_end or now, t) for t in times])
        return duration

    def get_working_duration(self):
        self.ensure_one()
        now = fields.Datetime.now()
        return self._intervals_duration([(t.date_start, now, t) for t in self.time_ids if not t.date_end])

    def get_productive_duration(self):
        self.ensure_one()
        now = fields.Datetime.now()
        productive_times = []
        for time in self.time_ids:
            if time.loss_id.loss_type == "productive":
                productive_times.append(time)
        duration = self._intervals_duration([(t.date_start, t.date_end or now, t) for t in productive_times])
        return duration

    def _cal_cost(self):
        return super()._cal_cost() + sum(self.time_ids.mapped('total_cost'))

    def button_pending(self):
        for emp in self.employee_ids:
            self.stop_employee([emp.id])
        super().button_pending()

    def action_mark_as_done(self):
        if self.env.context.get('mrp_display'):
            main_employee_connected = self.env['hr.employee'].get_session_owner()
        else:
            main_employee_connected = self.env.user.employee_id.id

        for wo in self:
            if not main_employee_connected:
                raise UserError(_('You must be logged in to process some of these work orders.'))
            if len(wo.allowed_employees) != 0 and main_employee_connected not in [wo.id for wo in wo.allowed_employees]:
                raise UserError(_('You are not allow to work on some of these work orders.'))
            if wo.working_state == 'blocked':
                raise UserError(_('Please unblock the work center to start the work order'))
        self.button_finish()

        loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'productive')], limit=1)
        if len(loss_id) < 1:
            raise UserError(_("You need to define at least one productivity loss in the category 'Productive'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))

        wo.state = 'done'
        self._set_default_time_log(loss_id)

    def _set_default_time_log(self, loss_id):
        if self.env.context.get('mrp_display'):
            if (self.env.context.get('employee_id')):
                main_employee_connected = self.env.context.get('employee_id')
            else:
                main_employee_connected = self.env['hr.employee'].get_session_owner()
        else:
            main_employee_connected = self.env.user.employee_id.id
        productivity = []
        for wo in self:
            if not wo.time_ids:
                now = fields.Datetime.now()
                date_start = datetime.fromtimestamp(now.timestamp() - ((wo.duration_expected * 60) // 1))
                date_end = now
                if not self.env.context.get('mrp_display') and wo.employee_assigned_ids:
                    main_employee_connected = wo.employee_assigned_ids[0].id
                productivity.append({
                    'workorder_id': wo.id,
                    'workcenter_id': wo.workcenter_id.id,
                    'description': _('Time Tracking: %(user)s', user=self.env.user.name),
                    'date_start': date_start,
                    'date_end': date_end,
                    'loss_id': loss_id[0].id,
                    'user_id': self.env.user.id,
                    'company_id': wo.company_id.id,
                    'employee_id': main_employee_connected
                })
        self.env['mrp.workcenter.productivity'].create(productivity)

    def _compute_expected_operation_cost(self):
        expected_machine_cost = super()._compute_expected_operation_cost()
        expected_labour_cost = (self.duration_expected / 60) * self.workcenter_id.employee_costs_hour * (self.operation_id.employee_ratio or 1)
        return expected_machine_cost + expected_labour_cost

    def _compute_current_operation_cost(self):
        current_machine_cost = super()._compute_current_operation_cost()
        current_labour_cost = sum(self.time_ids.mapped('total_cost'))
        return current_machine_cost + current_labour_cost

    def end_all(self):
        self.employee_ids = [Command.clear()]
        return super().end_all()

    def action_mrp_workorder_dependencies(self, action_name):
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.action_mrp_workorder_%s' % action_name)
        ref = 'mrp_workorder.workcenter_line_gantt_production_dependencies' if action_name == 'production' else 'mrp_workorder.mrp_workorder_view_gantt_dependencies'

        if self.env.user.has_group('mrp.group_mrp_workorder_dependencies'):
            action['views'] = [(self.env.ref(ref).id, 'gantt')] + [(id, kind) for id, kind in action['views'] if kind != 'gantt']
        return action
