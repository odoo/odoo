# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from re import findall as regex_findall
from re import split as regex_split

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"
    _inherit = ["mrp.abstract.workorder"]

    @api.model
    def default_get(self, fields):
        res = super(MrpProductProduce, self).default_get(fields)
        production = self.env['mrp.production']
        production_id = self.env.context.get('default_production_id') or self.env.context.get('active_id')
        if production_id:
            production = self.env['mrp.production'].browse(production_id)
        if production.exists():
            serial_finished = (production.product_id.tracking == 'serial')
            serial_batch_creation = production.serial_batch_creation
            todo_uom = production.product_uom_id
            todo_quantity = self._get_todo(production)
            if serial_finished:
                if production.product_uom_id.uom_type != 'reference':
                    todo_uom = self.env['uom.uom'].search([('category_id', '=', production.product_uom_id.category_id.id), ('uom_type', '=', 'reference')])
                if not serial_batch_creation:
                    todo_quantity = 1.0
                else:
                    todo_quantity = production.product_uom_id._compute_quantity(
                        todo_quantity,
                        todo_uom,
                        round=False
                    )
            if 'production_id' in fields:
                res['production_id'] = production.id
            if 'product_id' in fields:
                res['product_id'] = production.product_id.id
            if 'product_uom_id' in fields:
                res['product_uom_id'] = todo_uom.id
            if 'serial' in fields:
                res['serial'] = bool(serial_finished)
            if 'qty_producing' in fields:
                res['qty_producing'] = todo_quantity
            if 'next_serial_count' in fields:
                res['next_serial_count'] = todo_quantity
            if 'consumption' in fields:
                res['consumption'] = production.bom_id.consumption
            if 'serial_batch_creation' in fields:
                res['serial_batch_creation'] = serial_batch_creation
        return res

    serial = fields.Boolean('Requires Serial')
    next_serial = fields.Char('First SN')
    next_serial_count = fields.Integer('Number of SN')
    product_tracking = fields.Selection(related="product_id.tracking")
    is_pending_production = fields.Boolean(compute='_compute_pending_production')

    move_raw_ids = fields.One2many(related='production_id.move_raw_ids', string="PO Components")
    move_finished_ids = fields.One2many(related='production_id.move_finished_ids')

    raw_workorder_line_ids = fields.One2many('mrp.product.produce.line',
        'raw_product_produce_id', string='Components')
    finished_workorder_line_ids = fields.One2many('mrp.product.produce.line',
        'finished_product_produce_id', string='By-products')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',
        required=True, ondelete='cascade')

    serial_batch_creation = fields.Boolean(help='True if allow to produce Serial Number tracked product in batch')

    @api.onchange('qty_producing')
    def _onchange_qty_producing(self):
        if not self.serial_batch_creation:
            super()._onchange_qty_producing()

    def _update_workorder_lines(self):
        """ Update workorder lines, according to the new qty currently
        produced. It returns a dict with line to create, update or delete.
        It do not directly write or unlink the line because this function is
        used in onchange and request that write on db (e.g. workorder creation).
        """
        if not self.serial_batch_creation:
            return super()._update_workorder_lines()

        line_values = {'to_create': [], 'to_delete': [], 'to_update': {}}
        # moves are actual records
        move_raw_ids = self.move_raw_ids._origin.filtered(lambda move: move.state not in ('done', 'cancel'))
        for move in move_raw_ids:
            move_workorder_lines = self.raw_workorder_line_ids.filtered(lambda w: w.move_id == move)

            # Compute the new quantity for the current component
            rounding = move.product_uom.rounding
            new_qty = self._prepare_component_quantity(move, 1.0)
            new_qty = self.product_uom_id._compute_quantity(
                new_qty,
                self.production_id.product_uom_id,
                round=False
            )
            # for each finished product, the number of component we need to consume
            qty_todo = float_round(new_qty, precision_rounding=rounding)
            # total number changed of finished product
            qty_total = len(self.finished_workorder_line_ids) - len(move_workorder_lines)

            if float_compare(qty_total, 0.0, precision_rounding=rounding) < 0:
                move_workorder_lines = move_workorder_lines.sorted(key=lambda wl: wl._unreserve_order())
                if line_values['to_delete']:
                    line_values['to_delete'] |= move_workorder_lines[:-qty_total]
                else:
                    line_values['to_delete'] = move_workorder_lines[:-qty_total]
            else:
                line_values['to_create'].extend(self._generate_lines_values_in_batch(move, qty_todo, qty_total))

        return line_values

    def _generate_lines_values_in_batch(self, move, qty_todo, qty_total):
        """Generate raw workorder lines for serial number tracked product in
        batch.

        Args:
            move: Coresponding move of the component.
            qty_todo: Number of components need for each product.
            qty_total: Total number of products we create for.

        Return:
            A list of workorder line values.
        """
        move_workorder_lines = self._workorder_line_ids().filtered(lambda w: w.move_id == move)
        qty_current = len(move_workorder_lines)
        qty_producing = int(self.qty_producing)

        has_last_reserved = False
        if qty_current >= qty_producing:
            qty_reserved = 0
            qty_no_reserved = qty_total
        elif qty_total + qty_current >= qty_producing:
            # when perpare the value for the the last product we reserved, in order
            # to avoid the rounding error introduced by the previous line, we just
            # use what is left for the last product.
            has_last_reserved = True
            qty_reserved = qty_producing - qty_current
            qty_no_reserved = qty_total - qty_reserved
            last_to_consume = move.product_uom_qty - sum(move.move_line_ids.mapped('qty_done')) - qty_todo * (qty_reserved - 1) - sum(move_workorder_lines.mapped('qty_reserved'))
        else:
            qty_reserved = qty_total
            qty_no_reserved = 0

        if has_last_reserved:
            lines = [{
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_id.uom_id.id,
                'qty_to_consume': qty_todo,
                'qty_reserved': qty_todo,
                'qty_done': qty_todo,
                self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id,
            }] * (qty_reserved - 1)
            lines.append({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_id.uom_id.id,
                'qty_to_consume': last_to_consume,
                'qty_reserved': last_to_consume,
                'qty_done': last_to_consume,
                self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id
            })
        else:
            lines = [{
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_id.uom_id.id,
                'qty_to_consume': qty_todo,
                'qty_reserved': qty_todo,
                'qty_done': qty_todo,
                self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id,
            }] * qty_reserved

        lines.extend([{
            'move_id': move.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'qty_to_consume': qty_todo,
            'qty_done': qty_todo,
            self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id
        }] * qty_no_reserved)
        return lines

    @api.depends('qty_producing')
    def _compute_pending_production(self):

        """ Compute if it exits remaining quantity once the quantity on the
        current wizard will be processed. The purpose is to display or not
        button 'continue'.
        """
        for product_produce in self:
            remaining_qty = product_produce._get_todo(product_produce.production_id)
            product_produce.is_pending_production = remaining_qty - product_produce.qty_producing > 0.0

    def continue_production(self):
        """ Save current wizard and directly opens a new. """
        self.ensure_one()
        self._record_production()
        action = self.production_id.open_produce_product()
        action['context'] = {'default_production_id': self.production_id.id}
        return action

    def action_generate_serial(self):
        self.ensure_one()
        product_produce_wiz = self.env.ref('mrp.view_mrp_product_produce_wizard', False)
        self.finished_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.production_id.company_id.id
        })
        return {
            'name': _('Produce'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.product.produce',
            'res_id': self.id,
            'view_id': product_produce_wiz.id,
            'target': 'new',
        }

    def do_produce(self):
        """ Save the current wizard and go back to the MO. """
        self.ensure_one()
        self._record_production()
        self._check_company()
        return {'type': 'ir.actions.act_window_close'}

    def _get_todo(self, production):
        """ This method will return remaining todo quantity of production. """
        main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
        todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
        todo_quantity = todo_quantity if (todo_quantity > 0) else 0
        return todo_quantity

    def _record_production(self):
        # Check all the product_produce line have a move id (the user can add product
        # to consume directly in the wizard)
        for line in self._workorder_line_ids():
            line._check_line_sn_uniqueness()
        # because of an ORM limitation (fields on transient models are not
        # recomputed by updates in non-transient models), the related fields on
        # this model are not recomputed by the creations above
        self.invalidate_cache(['move_raw_ids', 'move_finished_ids'])

        # Save product produce lines data into stock moves/move lines
        quantity = self.qty_producing
        if self.serial_batch_creation:
            quantity = len(self.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.product_id))
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("The production order for '%s' has no quantity specified.") % self.product_id.display_name)

        self._check_sn_uniqueness()
        self._update_finished_move()
        self._update_moves()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'date_start': datetime.now(),
            })

    def _update_finished_move(self):
        if not self.serial_batch_creation:
            super()._update_finished_move()
        else:
            for line in self.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.product_id):
                if not line.lot_name:
                    raise UserError(_('You need to provide a serial number for the finished product.'))
                line.lot_id = self.finished_lot_id.create({
                    'name': line.lot_name,
                    'product_id': self.product_id.id,
                    'company_id': self.company_id.id,
                })
                self.qty_producing = 1.0
                self.finished_lot_id = line.lot_id
                super()._update_finished_move()

    def _generate_serial_numbers(self):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a workorder line for each generated `lot_name`.
        """
        self.ensure_one()
        if not self.next_serial:
            raise UserError(_("You need to set a Serial Number before generating more."))
        if not self.next_serial_count or self.next_serial_count <= 0:
            raise UserError(_('You have to produce at least one %s.') % self.product_uom_id.name)

        lot_names = self.env['stock.move']._generate_serial_number_names(self.next_serial, self.next_serial_count)
        lines = self._generate_finished_workorder_lines(lot_names)
        # without this, it won't be shown in the view
        self.finished_workorder_line_ids |= lines
        self.onchange_finished_workorder_line_ids()

    def _generate_finished_workorder_lines(self, lot_names):
        """Generate workorder lines for the products in batch according to the
        lot names we provide.
        """
        move_produced = self.move_finished_ids._origin.filtered(lambda move: move.product_id == self.product_id and move.state not in ('done', 'cancel'))
        lines_values = self._generate_lines_values(move_produced, len(lot_names))
        lines = self.env['mrp.product.produce.line']
        for values, lot_name in zip(lines_values, lot_names):
            values.update({'lot_name': lot_name})
            lines |= self.env[self._workorder_line_ids()._name].new(values)
        return lines

    def action_assign_serial_show_details(self):
        """Auto-generate SN and update the wizard.
        """
        self._generate_serial_numbers()
        return {
            'name': _('Produce'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.product.produce',
            'res_id': self.id,
            'view_id': self.env.ref('mrp.view_mrp_product_produce_wizard_batch', False).id,
            'target': 'new',
        }

    def _update_moves(self):
        """ Once the production is done. Modify the workorder lines into
        stock move line with the registered lot and quantity done.
        """
        # add missing move for extra component/byproduct
        for line in self._workorder_line_ids():
            if not line.move_id:
                line._set_move_id()
        # Before writting produce quantities, we ensure they respect the bom strictness
        self._strict_consumption_check()
        vals_list = []
        workorder_lines_to_process = self._workorder_line_ids().filtered(lambda line: line.product_id != self.product_id and line.qty_done > 0)
        components = self.production_id.bom_id.bom_line_ids.mapped('product_id')
        # group the workorder lines by their product so that we can set finished lots for the raw_workorder_line_ids
        grouped_workorder_lines_to_process = self._group_workorder_lines_by_product(workorder_lines_to_process)
        if self.serial_batch_creation:
            finished_lots = self.finished_workorder_line_ids.filtered(lambda l: l.product_id == self.product_id).mapped('lot_id')
        for product, lines in grouped_workorder_lines_to_process.items():
            if product in components and self.serial_batch_creation:
                for line, lots in zip(lines, finished_lots):
                    line._update_move_lines(lots)
                    if float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding) > 0:
                        vals_list += line._create_extra_move_lines()
            else:
                for line in lines:
                    if line.lot_name:
                        line.lot_id = line.lot_id.create({
                            'name': line.lot_name,
                            'product_id': line.product_id.id,
                            'company_id': line.company_id.id,
                        })
                    line._update_move_lines()
                    if float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding) > 0:
                        vals_list += line._create_extra_move_lines()

        self._workorder_line_ids().filtered(lambda line: line.product_id != self.product_id).unlink()
        self.env['stock.move.line'].create(vals_list)

    @api.model
    def _group_workorder_lines_by_product(self, workorder_lines):
        products = workorder_lines.mapped('product_id')
        grouped_workorder_lines = {}
        for line in workorder_lines:
            grouped_workorder_lines[line.product_id] = grouped_workorder_lines.get(line.product_id, self.env['mrp.product.produce.line']) | line
        return grouped_workorder_lines

    @api.onchange('finished_workorder_line_ids')
    def onchange_finished_workorder_line_ids(self):
        if self.serial_batch_creation:
            # split the line if lot name contains breaking char
            breaking_char = '\n'
            for line in self.finished_workorder_line_ids:
                # Look if the `lot_name` contains multiple values.
                if breaking_char in (line.lot_name or ''):
                    split_lines = line.lot_name.split(breaking_char)
                    split_lines = list(filter(None, split_lines))
                    line.lot_name = split_lines[0]
                    self._generate_finished_workorder_lines(split_lines[1:])

            # update components
            line_values = self._update_workorder_lines()
            for values in line_values['to_create']:
                self.raw_workorder_line_ids |= self.env[self._workorder_line_ids()._name].new(values)
            for line in line_values['to_delete']:
                if line in self.raw_workorder_line_ids:
                    self.raw_workorder_line_ids -= line
                else:
                    self.finished_workorder_line_ids -= line
            for line, vals in line_values['to_update'].items():
                line.update(vals)


class MrpProductProduceLine(models.TransientModel):
    _name = 'mrp.product.produce.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Record production line"

    raw_product_produce_id = fields.Many2one('mrp.product.produce', 'Component in Produce wizard')
    finished_product_produce_id = fields.Many2one('mrp.product.produce', 'Finished Product in Produce wizard')
    lot_name = fields.Text('Serial Number')

    @api.model
    def _get_raw_workorder_inverse_name(self):
        return 'raw_product_produce_id'

    @api.model
    def _get_finished_workoder_inverse_name(self):
        return 'finished_product_produce_id'

    def _get_final_lots(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.finished_lot_id | product_produce_id.finished_workorder_line_ids.mapped('lot_id')

    def _get_production(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.production_id
