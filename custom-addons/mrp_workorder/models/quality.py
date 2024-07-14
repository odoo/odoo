# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare, float_round, is_html_empty


class TestType(models.Model):
    _inherit = "quality.point.test_type"

    allow_registration = fields.Boolean(
        search='_get_domain_from_allow_registration',
        store=False, default=False)

    def _get_domain_from_allow_registration(self, operator, value):
        if value:
            return []
        else:
            return [('technical_name', 'not in', ['register_byproducts', 'register_consumed_materials', 'print_label'])]


class MrpRouting(models.Model):
    _inherit = "mrp.routing.workcenter"

    quality_point_ids = fields.One2many('quality.point', 'operation_id', copy=True)
    quality_point_count = fields.Integer('Instructions', compute='_compute_quality_point_count')

    employee_ratio = fields.Float("Employee Capacity", default=1, help="Number of employees needed to complete operation.")

    @api.depends('quality_point_ids')
    def _compute_quality_point_count(self):
        read_group_res = self.env['quality.point'].sudo()._read_group(
            [('id', 'in', self.quality_point_ids.ids)],
            ['operation_id'], ['__count']
        )
        data = {operation.id: count for operation, count in read_group_res}
        for operation in self:
            operation.quality_point_count = data.get(operation.id, 0)

    def write(self, vals):
        res = super().write(vals)
        if 'bom_id' in vals:
            self.quality_point_ids._change_product_ids_for_bom(self.bom_id)
        return res

    def copy(self, default=None):
        res = super().copy(default)
        if default and "bom_id" in default:
            res.quality_point_ids._change_product_ids_for_bom(res.bom_id)
        return res

    def toggle_active(self):
        self.with_context(active_test=False).quality_point_ids.toggle_active()
        return super().toggle_active()

    def action_mrp_workorder_show_steps(self):
        self.ensure_one()
        if self.bom_id.picking_type_id:
            picking_type_ids = self.bom_id.picking_type_id.ids
        else:
            picking_type_ids = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).ids
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_workorder_show_steps")
        ctx = {
            'default_company_id': self.company_id.id,
            'default_operation_id': self.id,
            'default_picking_type_ids': picking_type_ids,
        }
        action.update({'context': ctx, 'domain': [('operation_id', '=', self.id)]})
        return action

    def _get_fields_for_tablet(self):
        """ List of fields on the operation object that are needed by the tablet
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        return [
            'worksheet',
            'worksheet_google_slide',
            'id',
        ]


class QualityPoint(models.Model):
    _inherit = "quality.point"

    def _default_product_ids(self):
        # Determines a default product from the default operation's BOM.
        operation_id = self.env.context.get('default_operation_id')
        if operation_id:
            bom = self.env['mrp.routing.workcenter'].browse(operation_id).bom_id
            return bom.product_id.ids if bom.product_id else bom.product_tmpl_id.product_variant_id.ids

    is_workorder_step = fields.Boolean(compute='_compute_is_workorder_step')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Step', check_company=True)
    bom_id = fields.Many2one(related='operation_id.bom_id')
    bom_active = fields.Boolean('Related Bill of Material Active', related='bom_id.active')
    component_ids = fields.One2many('product.product', compute='_compute_component_ids')
    product_ids = fields.Many2many(
        default=_default_product_ids,
        domain="operation_id and [('id', 'in', bom_product_ids)] or [('type', 'in', ('product', 'consu')), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    bom_product_ids = fields.One2many('product.product', compute="_compute_bom_product_ids")
    test_type_id = fields.Many2one(
        'quality.point.test_type',
        domain="[('allow_registration', '=', operation_id and is_workorder_step)]")
    test_report_type = fields.Selection([('pdf', 'PDF'), ('zpl', 'ZPL')], string="Report Type", default="pdf", required=True)
    source_document = fields.Selection(
        selection=[('operation', 'Specific Page of Operation Worksheet'), ('step', 'Custom')],
        string="Step Document",
        default='operation')
    worksheet_page = fields.Integer('Worksheet Page', default=1)
    worksheet_document = fields.Binary('Image/PDF')
    worksheet_url = fields.Char('Google doc URL')
    # Used with type register_consumed_materials the product raw to encode.
    component_id = fields.Many2one('product.product', 'Product To Register', check_company=True)

    @api.onchange('bom_product_ids', 'is_workorder_step')
    def _onchange_bom_product_ids(self):
        if self.is_workorder_step and self.bom_product_ids:
            self.product_ids = self.product_ids & self.bom_product_ids
            self.product_category_ids = False

    @api.depends('bom_id.product_id', 'bom_id.product_tmpl_id.product_variant_ids', 'is_workorder_step', 'bom_id')
    def _compute_bom_product_ids(self):
        self.bom_product_ids = False
        points_for_workorder_step = self.filtered(lambda p: p.operation_id and p.bom_id)
        for point in points_for_workorder_step:
            bom_product_ids = point.bom_id.product_id or point.bom_id.product_tmpl_id.product_variant_ids
            point.bom_product_ids = bom_product_ids.filtered(lambda p: not p.company_id or p.company_id == point.company_id._origin)

    @api.depends('product_ids', 'test_type_id', 'is_workorder_step')
    def _compute_component_ids(self):
        self.component_ids = False
        for point in self:
            if point.test_type == 'register_byproducts':
                point.component_ids = point.bom_id.byproduct_ids.product_id
            else:
                bom_products = point.bom_id.product_id or point.bom_id.product_tmpl_id.product_variant_ids
                # If product_ids is set the step will exist only for these product variant then we can filter out for the bom explode
                if point.product_ids:
                    bom_products &= point.product_ids._origin

                component_product_ids = set()
                for product in bom_products:
                    dummy, lines_done = point.bom_id.explode(product, 1.0)
                    component_product_ids |= {line[0].product_id.id for line in lines_done}
                point.component_ids = self.env['product.product'].browse(component_product_ids)

    @api.depends('operation_id', 'picking_type_ids')
    def _compute_is_workorder_step(self):
        for quality_point in self:
            quality_point.is_workorder_step = quality_point.picking_type_ids and\
                all(pt.code == 'mrp_operation' for pt in quality_point.picking_type_ids)

    def _change_product_ids_for_bom(self, bom_id):
        products = bom_id.product_id or bom_id.product_tmpl_id.product_variant_ids
        self.product_ids = [Command.set(products.ids)]

    def _get_comparison_values(self):
        if not self:
            return False
        self.ensure_one()
        return tuple(self[key] for key in ('test_type_id', 'title', 'component_id', 'sequence'))

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if self.operation_id:
            self._change_product_ids_for_bom(self.bom_id)

    @api.onchange('test_type_id')
    def _onchange_test_type_id(self):
        if self.test_type_id.technical_name not in ('register_byproducts', 'register_consumed_materials'):
            self.component_id = False


class QualityAlert(models.Model):
    _inherit = "quality.alert"

    workorder_id = fields.Many2one('mrp.workorder', 'Operation', check_company=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', check_company=True)
    production_id = fields.Many2one('mrp.production', "Production Order", check_company=True)


class QualityCheck(models.Model):
    _inherit = "quality.check"

    workorder_id = fields.Many2one(
        'mrp.workorder', 'Operation', check_company=True, index='btree_not_null')
    workcenter_id = fields.Many2one('mrp.workcenter', related='workorder_id.workcenter_id', store=True, readonly=True)  # TDE: necessary ?
    production_id = fields.Many2one(
        'mrp.production', 'Production Order', check_company=True, index='btree_not_null')
    product_tracking = fields.Selection(related='production_id.product_tracking')

    # doubly linked chain for tablet view navigation
    next_check_id = fields.Many2one('quality.check')
    previous_check_id = fields.Many2one('quality.check')

    # For components registration
    move_id = fields.Many2one(
        'stock.move', 'Stock Move', check_company=True)
    move_line_id = fields.Many2one(
        'stock.move.line', 'Stock Move Line', check_company=True)
    component_id = fields.Many2one(
        'product.product', 'Component', check_company=True)
    component_uom_id = fields.Many2one('uom.uom', related='move_id.product_uom', readonly=True)

    qty_done = fields.Float('Done', digits='Product Unit of Measure')
    finished_lot_id = fields.Many2one('stock.lot', 'Finished Lot/Serial', related='production_id.lot_producing_id', store=True)
    additional = fields.Boolean('Register additional product', compute='_compute_additional')
    component_tracking = fields.Selection(related='component_id.tracking', string="Is Component Tracked")

    # Workorder specific fields
    component_remaining_qty = fields.Float('Remaining Quantity for Component', compute='_compute_component_data', digits='Product Unit of Measure')
    component_qty_to_do = fields.Float(compute='_compute_component_qty_to_do', digits='Product Unit of Measure')
    is_user_working = fields.Boolean(related="workorder_id.is_user_working")
    consumption = fields.Selection(related="workorder_id.consumption")
    working_state = fields.Selection(related="workorder_id.working_state")
    is_deleted = fields.Boolean('Deleted in production')

    # Computed fields
    title = fields.Char('Title', compute='_compute_title')
    result = fields.Char('Result', compute='_compute_result')

    # Used to group the steps belonging to the same production
    # We use a float because it is actually filled in by the produced quantity at the step creation.
    finished_product_sequence = fields.Float('Finished Product Sequence Number')
    worksheet_document = fields.Binary('Image/PDF')
    worksheet_url = fields.Char(related='point_id.worksheet_url')
    worksheet_page = fields.Integer(related='point_id.worksheet_page')
    source_document = fields.Selection(related='point_id.source_document')

    # Employees
    employee_id = fields.Many2one('hr.employee', string="Employee")

    @api.model_create_multi
    def create(self, values):
        points = self.env['quality.point'].search([
            ('id', 'in', [value.get('point_id') for value in values]),
            ('component_id', '!=', False)
        ])
        for value in values:
            if not value.get('component_id') and value.get('point_id'):
                point = points.filtered(lambda p: p.id == value.get('point_id'))
                if point:
                    value['component_id'] = point.component_id.id
        return super(QualityCheck, self).create(values)

    @api.depends('test_type_id', 'component_id', 'component_id.name', 'workorder_id', 'workorder_id.name')
    def _compute_title(self):
        super()._compute_title()
        for check in self:
            if not check.point_id and check.component_id:
                check.title = '{} "{}"'.format(check.test_type_id.display_name, check.component_id.name or check.workorder_id.name)

    @api.depends('point_id', 'quality_state', 'component_id', 'component_uom_id', 'lot_id', 'qty_done')
    def _compute_result(self):
        for check in self:
            if check.quality_state == 'none':
                check.result = ''
            else:
                check.result = check._get_check_result()

    @api.depends('move_id')
    def _compute_additional(self):
        """ The stock_move is linked to additional workorder line only at
        record_production. So line without move during production are additionnal
        ones. """
        for check in self:
            check.additional = not check.move_id

    @api.depends('qty_done', 'component_remaining_qty')
    def _compute_component_qty_to_do(self):
        for wo in self:
            wo.component_qty_to_do = wo.qty_done - wo.component_remaining_qty

    def _get_check_result(self):
        if self.test_type in ('register_consumed_materials', 'register_byproducts') and self.lot_id:
            return '{} - {}, {} {}'.format(self.component_id.name, self.lot_id.name, self.qty_done, self.component_uom_id.name)
        elif self.test_type in ('register_consumed_materials', 'register_byproducts'):
            return '{}, {} {}'.format(self.component_id.name, self.qty_done, self.component_uom_id.name)
        else:
            return ''

    @api.depends('workorder_id.state', 'quality_state', 'workorder_id.qty_producing',
                 'component_tracking', 'test_type', 'component_id', 'move_line_id.lot_id'
                 )
    def _compute_component_data(self):
        self.component_remaining_qty = False
        self.component_uom_id = False
        for check in self:
            if check.test_type in ('register_byproducts', 'register_consumed_materials'):
                if check.quality_state == 'none':
                    completed_lines = check.workorder_id.move_line_ids.filtered(lambda l: l.picked and (check.component_id.tracking == 'none' or l.lot_id))
                    if check.move_id.additional:
                        qty = check.workorder_id.qty_remaining
                    else:
                        qty = check.workorder_id.qty_producing
                    check.component_remaining_qty = self._prepare_component_quantity(check.move_id, qty) - sum(completed_lines.mapped('quantity'))
                check.component_uom_id = check.move_id.product_uom

    def action_print(self):
        quality_point_id = self.point_id
        report_type = quality_point_id.test_report_type

        if self.product_id.tracking == 'none':
            res = self._get_product_label_action(report_type)
        else:
            if self.workorder_id.finished_lot_id:
                res = self._get_lot_label_action(report_type)
            else:
                raise UserError(_('You did not set a lot/serial number for '
                                'the final product'))

        # The button goes immediately to the next step
        self._next()
        return res

    def _get_print_qty(self):
        if self.product_id.uom_id.category_id == self.env.ref('uom.product_uom_categ_unit'):
            qty = int(self.workorder_id.qty_producing)
        else:
            qty = 1
        return qty

    def _get_product_label_action(self, report_type):
        self.ensure_one()
        xml_id = 'product.action_open_label_layout'
        wizard_action = self.env['ir.actions.act_window']._for_xml_id(xml_id)
        wizard_action['context'] = {'default_product_ids': self.product_id.ids}
        if report_type == 'zpl':
            wizard_action['context']['default_print_format'] = 'zpl'
        wizard_action['id'] = self.env.ref(xml_id).id
        return wizard_action

    def _get_lot_label_action(self, report_type):
        qty = self._get_print_qty()

        if report_type == 'zpl':
            xml_id = 'stock.label_lot_template'
        else:
            xml_id = 'stock.action_report_lot_label'
        res = self.env.ref(xml_id).report_action([self.workorder_id.finished_lot_id.id] * qty)
        res['id'] = self.env.ref(xml_id).id
        return res

    def action_next(self):
        self.ensure_one()
        return self._next()

    def action_continue(self):
        self.ensure_one()
        self._next(continue_production=True)

    def add_check_in_chain(self, activity=True):
        self.ensure_one()
        if self.workorder_id.current_quality_check_id:
            self._insert_in_chain('after', self.workorder_id.current_quality_check_id)
        else:
            self.workorder_id.current_quality_check_id = self
        if self.workorder_id.production_id.bom_id and activity:
            tl_text = _("New Step suggested by %(user_name)s", user_name=self.env.user.name)
            body = Markup("<b>%s</b>") % tl_text
            if self.note and not is_html_empty(self.note):
                tl_text = _("Instruction:")
                body += Markup("<br/><b>%s</b>%s") % (tl_text, self.note)
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': self.workorder_id.production_id.bom_id.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.title or self.test_type, self.workorder_id.production_id.name),
                'note': body,
            })

    @api.model
    def _prepare_component_quantity(self, move, qty_producing):
        """ helper that computes quantity to consume (or to create in case of byproduct)
        depending on the quantity producing and the move's unit factor"""
        if move.product_id.tracking == 'serial':
            uom = move.product_id.uom_id
        else:
            uom = move.product_uom
        return move.product_uom._compute_quantity(
            qty_producing * move.unit_factor,
            uom,
            round=False
        )

    def _create_extra_move_lines(self):
        """Create new sml if quantity produced is bigger than the reserved one"""
        vals_list = []
        # apply putaway
        location_dest_id = self.move_id.location_dest_id._get_putaway_strategy(self.move_id.product_id)
        quants = self.env['stock.quant']._gather(self.product_id, self.move_id.location_id, lot_id=self.lot_id, strict=False)
        # Search for a sub-locations where the product is available.
        # Loop on the quants to get the locations. If there is not enough
        # quantity into stock, we take the move location. Anyway, no
        # reservation is made, so it is still possible to change it afterwards.
        move_uom = self.move_id.product_uom
        shared_vals = {
            'move_id': self.move_id.id,
            'product_id': self.move_id.product_id.id,
            'location_dest_id': location_dest_id.id,
            'product_uom_id': move_uom.id,
            'lot_id': self.lot_id.id,
            'company_id': self.move_id.company_id.id,
        }
        qty_done = self.qty_done
        for quant in quants:
            vals = shared_vals.copy()
            quantity = quant.quantity - quant.reserved_quantity
            quantity = self.component_id.uom_id._compute_quantity(quantity, move_uom, rounding_method='HALF-UP')
            rounding = quant.product_uom_id.rounding
            if (float_compare(quant.quantity, 0, precision_rounding=rounding) <= 0 or
                    float_compare(quantity, 0, precision_rounding=move_uom.rounding) <= 0):
                continue
            vals.update({
                'location_id': quant.location_id.id,
                'quantity': min(quantity, qty_done),
                'picked': True,
            })

            vals_list.append(vals)
            qty_done -= vals['quantity']
            # If all the qty_done is distributed, we can close the loop
            if float_compare(qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
                break

        if float_compare(qty_done, 0, precision_rounding=self.product_id.uom_id.rounding) > 0:
            vals = shared_vals.copy()
            vals.update({
                'location_id': self.move_id.location_id.id,
                'quantity': qty_done,
                'picked': True,
            })

            vals_list.append(vals)
        return vals_list

    def action_generate_serial(self):
        self.ensure_one()
        self.production_id.action_generate_serial()
        self.lot_id = self.production_id.lot_producing_id

    def action_generate_serial_number_and_pass(self):
        self.action_generate_serial()
        if self.product_tracking == 'serial':
            self.qty_done = 1
        elif self.product_tracking == 'lot' and self.qty_done == 0:
            self.qty_done = self.production_id.product_qty
        return self._next()

    def _next(self, continue_production=False):
        """ This function:

        - first: fullfill related move line with right lot and validated quantity.
        - second: Generate new quality check for remaining quantity and link them to the original check.
        - third: Pass to the next check or return a failure message.
        """
        self.ensure_one()
        self.workorder_id.current_quality_check_id = self.id
        rounding = self.workorder_id.product_uom_id.rounding
        if self.test_type == 'register_production':
            if self.product_tracking != 'none':
                if not self.lot_id and self.qty_done != 0:
                    raise UserError(_('Please enter a Lot/SN.'))
                self.production_id.lot_producing_id = self.lot_id
            if float_compare(self.qty_done, 0, precision_rounding=rounding) <= 0:
                raise UserError(_('Please enter a positive quantity.'))
            self.workorder_id.production_id.qty_producing = self.qty_done
        elif self.test_type in ('register_byproducts', 'register_consumed_materials'):
            # Form validation
            # in case we use continue production instead of validate button.
            # We would like to consume 0 and leave lot_id blank to close the consumption
            rounding = self.component_uom_id.rounding
            if self.component_tracking != 'none' and not self.lot_id and self.qty_done != 0:
                raise UserError(_('Please enter a Lot/SN.'))
            if float_compare(self.qty_done, 0, precision_rounding=rounding) < 0:
                raise UserError(_('Please enter a positive quantity.'))

            # Write the lot and qty to the move line
            if self.move_line_id:
                # In case of a tracked component, another SML may already exists for
                # the reservation of self.lot_id, so let's try to find and use it
                if self.move_line_id.product_id.tracking != 'none':
                    self.move_line_id = next((sml
                                              for sml in self.move_line_id.move_id.move_line_ids
                                              if sml.lot_id == self.lot_id and not sml.picked),
                                             self.move_line_id)
                rounding = self.move_line_id.product_uom_id.rounding
                if float_compare(self.qty_done, self.move_line_id.quantity, precision_rounding=rounding) >= 0:
                    self.move_line_id.write({
                        'quantity': self.qty_done,
                        'lot_id': self.lot_id.id,
                        'picked': True,
                    })
                else:
                    new_qty_reserved = self.move_line_id.quantity - self.qty_done
                    default = {
                        'quantity': new_qty_reserved,
                    }
                    self.move_line_id.copy(default=default)
                    self.move_line_id.write({
                        'quantity': self.qty_done,
                        'picked': True,
                    })
                    self.move_line_id.lot_id = self.lot_id
            else:
                line = self.env['stock.move.line'].create(self._create_extra_move_lines())
                self.move_line_id = line[:1]
            if continue_production:
                self.workorder_id._create_subsequent_checks()

        if self.test_type == 'picture' and not self.picture:
            raise UserError(_('Please upload a picture.'))

        if self.quality_state == 'none':
            self.do_pass()

        self.workorder_id._change_quality_check(position='next')

    def _update_component_quantity(self):
        if self.component_tracking == 'serial':
            self._origin.qty_done = self.component_id.uom_id._compute_quantity(1, self.component_uom_id, rounding_method='HALF-UP')
            return
        move = self.move_id
        # Compute the new quantity for the current component
        rounding = move.product_uom.rounding
        new_qty = self._prepare_component_quantity(move, self.workorder_id.qty_producing)
        qty_todo = float_round(new_qty, precision_rounding=rounding)
        if (move.picked and self.quality_state != 'pass'):
            qty_todo = qty_todo - move.quantity
        if self.move_line_id and self.move_line_id.lot_id:
            qty_todo = min(self.move_line_id.quantity, qty_todo)
        self.qty_done = qty_todo

    def _insert_in_chain(self, position, relative):
        """Insert the quality check `self` in a chain of quality checks.

        The chain of quality checks is implicitly given by the `relative` argument,
        i.e. by following its `previous_check_id` and `next_check_id` fields.

        :param position: Where we need to insert `self` according to `relative`
        :type position: string
        :param relative: Where we need to insert `self` in the chain
        :type relative: A `quality.check` record.
        """
        self.ensure_one()
        assert position in ['before', 'after']
        if position == 'before':
            new_previous = relative.previous_check_id
            self.next_check_id = relative
            self.previous_check_id = new_previous
            new_previous.next_check_id = self
            relative.previous_check_id = self
        else:
            new_next = relative.next_check_id
            self.next_check_id = new_next
            self.previous_check_id = relative
            new_next.previous_check_id = self
            relative.next_check_id = self

    def _update_lots(self):
        for check in self:
            if check.component_tracking and check.move_id.picking_type_id.prefill_lot_tablet:
                check.lot_id = check.move_line_id.lot_id

    def do_pass(self):
        res = super().do_pass()
        for check in self:
            if check.workorder_id:
                if check.workorder_id.employee_id:
                    check.employee_id = self.workorder_id.employee_id
                if check.workorder_id.state == 'ready':
                    check.workorder_id.button_start(bypass=True)
        return res
