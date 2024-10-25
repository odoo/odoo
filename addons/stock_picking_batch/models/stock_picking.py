# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.osv import expression
from odoo.exceptions import ValidationError


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    count_picking_batch = fields.Integer(compute='_compute_picking_count')
    count_picking_wave = fields.Integer(compute='_compute_picking_count')
    auto_batch = fields.Boolean('Automatic Batches',
                                help="Automatically put pickings into batches as they are confirmed when possible.")
    batch_group_by_partner = fields.Boolean('Contact', help="Automatically group batches by contacts.")
    batch_group_by_destination = fields.Boolean('Destination Country', help="Automatically group batches by destination country.")
    batch_group_by_src_loc = fields.Boolean('Source Location',
                                            help="Automatically group batches by their source location.")
    batch_group_by_dest_loc = fields.Boolean('Destination Location',
                                             help="Automatically group batches by their destination location.")
    batch_max_lines = fields.Integer("Maximum lines per batch",
                                     help="A transfer will not be automatically added to batches that will exceed this number of lines if the transfer is added to it.\n"
                                          "Leave this value as '0' if no line limit.")
    batch_max_pickings = fields.Integer("Maximum transfers per batch",
                                        help="A transfer will not be automatically added to batches that will exceed this number of transfers.\n"
                                             "Leave this value as '0' if no transfer limit.")
    batch_auto_confirm = fields.Boolean("Auto-confirm", default=True)

    def _compute_picking_count(self):
        super()._compute_picking_count()
        data = self.env['stock.picking.batch']._read_group(
            [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
            ['picking_type_id', 'is_wave'], ['__count'])
        count = {(picking_type.id, is_wave): count for picking_type, is_wave, count in data}
        for record in self:
            record.count_picking_wave = count.get((record.id, True), 0)
            record.count_picking_batch = count.get((record.id, False), 0)

    @api.model
    def _get_batch_group_by_keys(self):
        return ['batch_group_by_partner', 'batch_group_by_destination', 'batch_group_by_src_loc', 'batch_group_by_dest_loc']

    @api.constrains(lambda self: self._get_batch_group_by_keys() + ['auto_batch'])
    def _validate_auto_batch_group_by(self):
        group_by_keys = self._get_batch_group_by_keys()
        for picking_type in self:
            if not picking_type.auto_batch:
                continue
            if not any(picking_type[key] for key in group_by_keys):
                raise ValidationError(_("If the Automatic Batches feature is enabled, at least one 'Group by' option must be selected."))

    def get_action_picking_tree_batch(self):
        return self._get_action('stock_picking_batch.stock_picking_batch_action')

    def get_action_picking_tree_wave(self):
        return self._get_action('stock_picking_batch.action_picking_tree_wave')


class StockPicking(models.Model):
    _inherit = "stock.picking"

    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Transfer',
        check_company=True,
        help='Batch associated to this transfer', index=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking, vals in zip(pickings, vals_list):
            if vals.get('batch_id'):
                if not picking.batch_id.picking_type_id:
                    picking.batch_id.picking_type_id = picking.picking_type_id[0]
                picking.batch_id._sanity_check()
        return pickings

    def write(self, vals):
        old_batches = self.batch_id
        res = super().write(vals)
        if vals.get('batch_id'):
            old_batches.filtered(lambda b: not b.picking_ids).state = 'cancel'
            if not self.batch_id.picking_type_id:
                self.batch_id.picking_type_id = self.picking_type_id[0]
            self.batch_id._sanity_check()
            # assign batch users to batch pickings
            self.batch_id.picking_ids.assign_batch_user(self.batch_id.user_id.id)
        return res

    def action_add_operations(self):
        view = self.env.ref('stock_picking_batch.view_move_line_tree_detailed_wave')
        return {
            'name': _('Add Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'view': view,
            'views': [(view.id, 'tree')],
            'res_model': 'stock.move.line',
            'target': 'new',
            'domain': [
                ('picking_id', 'in', self.ids),
                ('state', '!=', 'done')
            ],
            'context': dict(
                self.env.context,
                picking_to_wave=self.ids,
                active_wave_id=self.env.context.get('active_wave_id').id,
                search_default_by_location=True,
            )}

    def action_confirm(self):
        res = super().action_confirm()
        for picking in self:
            picking._find_auto_batch()
        return res

    def button_validate(self):
        res = super().button_validate()
        to_assign_ids = set()
        if self and self.env.context.get('pickings_to_detach'):
            pickings_to_detach = self.env['stock.picking'].browse(self.env.context['pickings_to_detach'])
            pickings_to_detach.batch_id = False
            pickings_to_detach.move_ids.filtered(lambda m: not m.quantity).picked = False
            to_assign_ids.update(self.env.context['pickings_to_detach'])

        for picking in self:
            if picking.state != 'done':
                continue
            # Avoid inconsistencies in states of the same batch when validating a single picking in a batch.
            if picking.batch_id and any(p.state != 'done' for p in picking.batch_id.picking_ids):
                picking.batch_id = None
            # If backorder were made, if auto-batch is enabled, seek a batch for each of them with the selected criterias.
            to_assign_ids.update(picking.backorder_ids.ids)

        # To avoid inconsistencies, all incorrect pickings must be removed before assigning backorder pickings
        assignable_pickings = self.env['stock.picking'].browse(to_assign_ids)
        for picking in assignable_pickings:
            picking._find_auto_batch()

        return res

    def _create_backorder(self):
        pickings_to_detach = self.env['stock.picking'].browse(self.env.context.get('pickings_to_detach'))
        for picking in self:
            # Avoid inconsistencies in states of the same batch when validating a single picking in a batch.
            if picking.batch_id and picking.state != 'done' and any(p not in self for p in picking.batch_id.picking_ids - pickings_to_detach):
                picking.batch_id = None
        return super()._create_backorder()

    def action_cancel(self):
        res = super().action_cancel()
        for picking in self:
            if picking.batch_id and any(picking.state != 'cancel' for picking in picking.batch_id.picking_ids):
                picking.batch_id = None
        return res

    def _should_show_transfers(self):
        if len(self.batch_id) == 1 and len(self) == (len(self.batch_id.picking_ids) - len(self.env.context.get('pickings_to_detach', []))):
            return False
        return super()._should_show_transfers()

    def _find_auto_batch(self):
        self.ensure_one()
        # Check if auto_batch is enabled for this picking.
        if not self.picking_type_id.auto_batch or self.batch_id or not self.move_ids or not self._is_auto_batchable():
            return False

        # Try to find a compatible batch to insert the picking
        possible_batches = self.env['stock.picking.batch'].sudo().search(self._get_possible_batches_domain())
        for batch in possible_batches:
            if batch._is_picking_auto_mergeable(self):
                batch.picking_ids |= self
                return batch

        # If no batch were found, try to find a compatible picking and put them both in a new batch.
        possible_pickings = self.env['stock.picking'].search(self._get_possible_pickings_domain())
        for picking in possible_pickings:
            if self._is_auto_batchable(picking):
                # Create new batch with both pickings
                new_batch = self.env['stock.picking.batch'].sudo().create({
                    'picking_ids': [Command.link(self.id), Command.link(picking.id)],
                    'company_id': self.company_id.id if self.company_id else False,
                    'picking_type_id': self.picking_type_id.id,
                })
                if picking.picking_type_id.batch_auto_confirm:
                    new_batch.action_confirm()
                return new_batch

        # If nothing was found after those two steps, then no batch is doable given the conditions
        return False

    def _is_auto_batchable(self, picking=None):
        """ Verifies if a picking can be put in a batch with another picking without violating auto_batch constrains.
        """
        if self.state != 'assigned':
            return False
        res = True
        if not picking:
            picking = self.env['stock.picking']
        if self.picking_type_id.batch_max_lines:
            res = res and (len(self.move_ids) + len(picking.move_ids) <= self.picking_type_id.batch_max_lines)
        if self.picking_type_id.batch_max_pickings:
            # Sounds absurd. BUT if we put "batch max picking" to a value <= 1, makes sense ... Or not. Because then there is no point to batch.
            res = res and self.picking_type_id.batch_max_pickings > 1
        return res

    def _get_possible_pickings_domain(self):
        self.ensure_one()
        domain = [
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id if self.company_id else False),
            ('state', '=', 'assigned'),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('batch_id', '=', False),
        ]
        if self.picking_type_id.batch_group_by_partner:
            domain = expression.AND([domain, [('partner_id', '=', self.partner_id.id)]])
        if self.picking_type_id.batch_group_by_destination:
            domain = expression.AND([domain, [('partner_id.country_id', '=', self.partner_id.country_id.id)]])
        if self.picking_type_id.batch_group_by_src_loc:
            domain = expression.AND([domain, [('location_id', '=', self.location_id.id)]])
        if self.picking_type_id.batch_group_by_dest_loc:
            domain = expression.AND([domain, [('location_dest_id', '=', self.location_dest_id.id)]])

        return domain

    def _get_possible_batches_domain(self):
        self.ensure_one()
        domain = [
            ('state', 'in', ('draft', 'in_progress') if self.picking_type_id.batch_auto_confirm else ('draft',)),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', self.company_id.id if self.company_id else False),
        ]
        if self.picking_type_id.batch_group_by_partner:
            domain = expression.AND([domain, [('picking_ids.partner_id', '=', self.partner_id.id)]])
        if self.picking_type_id.batch_group_by_destination:
            domain = expression.AND([domain, [('picking_ids.partner_id.country_id', '=', self.partner_id.country_id.id)]])
        if self.picking_type_id.batch_group_by_src_loc:
            domain = expression.AND([domain, [('picking_ids.location_id', '=', self.location_id.id)]])
        if self.picking_type_id.batch_group_by_dest_loc:
            domain = expression.AND([domain, [('picking_ids.location_dest_id', '=', self.location_dest_id.id)]])

        return domain

    def _package_move_lines(self, batch_pack=False):
        if batch_pack:
            return super(StockPicking, self.batch_id.picking_ids if self.batch_id else self)._package_move_lines(batch_pack)
        return super()._package_move_lines(batch_pack)

    def assign_batch_user(self, user_id):
        if not user_id:
            return
        pickings = self.filtered(lambda p: p.user_id.id != user_id)
        pickings.write({'user_id': user_id})
        for pick in pickings:
            log_message = _('Assigned to %s Responsible', pick.batch_id._get_html_link())
            pick.message_post(body=log_message)

    def action_view_batch(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.batch',
            'res_id': self.batch_id.id,
            'view_mode': 'form'
        }
