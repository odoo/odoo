# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _name = 'stock.picking.batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Batch Transfer"
    _order = "name desc"

    name = fields.Char(
        string='Batch Transfer', default='New',
        copy=False, required=True, readonly=True)
    description = fields.Char('Description')
    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True, readonly=True,
        index=True, default=lambda self: self.env.company)
    picking_ids = fields.One2many(
        'stock.picking', 'batch_id', string='Transfers',
        domain="[('id', 'in', allowed_picking_ids)]", check_company=True,
        help='List of transfers associated to this batch')
    show_check_availability = fields.Boolean(
        compute='_compute_move_ids',
        string='Show Check Availability')
    show_allocation = fields.Boolean(
        compute='_compute_show_allocation',
        string='Show Allocation Button')
    allowed_picking_ids = fields.One2many('stock.picking', compute='_compute_allowed_picking_ids')
    move_ids = fields.One2many(
        'stock.move', string="Stock moves", compute='_compute_move_ids')
    move_line_ids = fields.One2many(
        'stock.move.line', string='Stock move lines',
        compute='_compute_move_line_ids', inverse='_set_move_line_ids', search='_search_move_line_ids')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        store=True, compute='_compute_state',
        copy=False, tracking=True, required=True, readonly=True, index=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', check_company=True, copy=False,
        index=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', related='picking_type_id.warehouse_id')
    picking_type_code = fields.Selection(
        related='picking_type_id.code')
    scheduled_date = fields.Datetime(
        'Scheduled Date', copy=False, store=True, readonly=False, compute="_compute_scheduled_date",
        help="""Scheduled date for the transfers to be processed.
              - If manually set then scheduled date for all transfers in batch will automatically update to this date.
              - If not manually changed and transfers are added/removed/updated then this will be their earliest scheduled date
                but this scheduled date will not be set for all transfers in batch.""")
    is_wave = fields.Boolean('This batch is a wave')
    show_lots_text = fields.Boolean(compute='_compute_show_lots_text')
    estimated_shipping_weight = fields.Float(
        "shipping_weight", compute='_compute_estimated_shipping_capacity', digits='Product Unit')
    estimated_shipping_volume = fields.Float(
        "shipping_volume", compute='_compute_estimated_shipping_capacity', digits='Product Unit')
    properties = fields.Properties('Properties', definition='picking_type_id.batch_properties_definition', copy=True)

    @api.depends('description')
    @api.depends_context('add_to_existing_batch')
    def _compute_display_name(self):
        if not self.env.context.get('add_to_existing_batch'):
            return super()._compute_display_name()
        for batch in self:
            batch.display_name = f"{batch.name}: {batch.description}" if batch.description else batch.name

    @api.depends('picking_type_id')
    def _compute_show_lots_text(self):
        for batch in self:
            batch.show_lots_text = batch.picking_ids and batch.picking_ids[0].show_lots_text

    def _compute_estimated_shipping_capacity(self):
        for batch in self:
            estimated_shipping_weight = 0
            estimated_shipping_volume = 0
            done_package_ids = set()
            # packs
            for pack in self.move_line_ids.result_package_id:
                p_type = pack.package_type_id
                if pack.shipping_weight:
                    # shipping_weight was computed, so base_weight should be included.
                    estimated_shipping_weight += pack.shipping_weight
                    done_package_ids.add(pack.id)
                elif p_type:
                    estimated_shipping_weight += p_type.base_weight or 0
                    estimated_shipping_volume += (p_type.packaging_length * p_type.width * p_type.height) / 1000.0**3
            # move without packs
            for move_line in self.picking_ids.move_ids.move_line_ids:
                if move_line.result_package_id.id in done_package_ids:
                    continue
                estimated_shipping_weight += move_line.product_id.weight * move_line.quantity_product_uom
                estimated_shipping_volume += move_line.product_id.volume * move_line.quantity_product_uom
            batch.estimated_shipping_weight = estimated_shipping_weight
            batch.estimated_shipping_volume = estimated_shipping_volume

    @api.depends('company_id', 'picking_type_id', 'state')
    def _compute_allowed_picking_ids(self):
        allowed_picking_states = ['waiting', 'confirmed', 'assigned']

        for batch in self:
            domain_states = list(allowed_picking_states)
            # Allows to add draft pickings only if batch is in draft as well.
            if batch.state == 'draft':
                domain_states.append('draft')
            domain = [
                ('company_id', '=', batch.company_id.id),
                ('state', 'in', domain_states),
            ]
            if batch.picking_type_id:
                domain += [('picking_type_id', '=', batch.picking_type_id.id)]
            batch.allowed_picking_ids = self.env['stock.picking'].search(domain)

    @api.depends('picking_ids', 'picking_ids.move_line_ids', 'picking_ids.move_ids', 'picking_ids.move_ids.state')
    def _compute_move_ids(self):
        for batch in self:
            batch.move_ids = batch.picking_ids.move_ids
            batch.show_check_availability = any(m.state not in ['assigned', 'cancel', 'done'] for m in batch.move_ids)

    @api.depends('picking_ids', 'picking_ids.move_line_ids')
    def _compute_move_line_ids(self):
        for batch in self:
            batch.move_line_ids = batch.picking_ids.move_line_ids

    def _search_move_line_ids(self, operator, value):
        return [('picking_ids.move_line_ids',operator,value)]

    @api.depends('state', 'move_ids', 'picking_type_id')
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.env.user.has_group('stock.group_reception_report'):
            return
        for batch in self:
            batch.show_allocation = batch.picking_ids._get_show_allocation(batch.picking_type_id)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_state(self):
        batchs = self.filtered(lambda batch: batch.state not in ['cancel', 'done'])
        for batch in batchs:
            if not batch.picking_ids:
                continue
            # Cancels automatically the batch picking if all its transfers are cancelled.
            if all(picking.state == 'cancel' for picking in batch.picking_ids):
                batch.state = 'cancel'
            # Batch picking is marked as done if all its not canceled transfers are done.
            elif all(picking.state in ['cancel', 'done'] for picking in batch.picking_ids):
                batch.state = 'done'

    @api.depends('picking_ids', 'picking_ids.scheduled_date')
    def _compute_scheduled_date(self):
        for rec in self:
            rec.scheduled_date = min(rec.picking_ids.filtered('scheduled_date').mapped('scheduled_date'), default=False)

    @api.onchange('scheduled_date')
    def onchange_scheduled_date(self):
        if self.scheduled_date:
            self.picking_ids.scheduled_date = self.scheduled_date

    def _set_move_line_ids(self):
        new_move_lines = self[0].move_line_ids
        for picking in self.picking_ids:
            old_move_lines = picking.move_line_ids
            picking.move_line_ids = new_move_lines.filtered(lambda ml: ml.picking_id.id == picking.id)
            move_lines_to_unlink = old_move_lines - new_move_lines
            if move_lines_to_unlink:
                move_lines_to_unlink.unlink()

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company_id = vals.get('company_id', self.env.company.id)
                picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id'))
                if picking_type:
                    sequence_code = 'picking.wave' if vals.get('is_wave') else 'picking.batch'
                    vals['name'] = self._prepare_name(picking_type, sequence_code, company_id)
        return super().create(vals_list)

    def write(self, vals):
        batches_to_rename = self.env['stock.picking.batch']
        if vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id'))
            batches_to_rename = self.filtered(lambda b: b.picking_type_id != picking_type)
        res = super().write(vals)
        if not self.picking_ids:
            self.filtered(lambda b: b.state == 'in_progress').action_cancel()
        if vals.get('picking_type_id'):
            self._sanity_check()
            for batch in batches_to_rename:
                sequence_code = 'picking.wave' if batch.is_wave else 'picking.batch'
                batch.name = self._prepare_name(picking_type, sequence_code, batch.company_id)
        if vals.get('picking_ids'):
            batch_without_picking_type = self.filtered(lambda batch: not batch.picking_type_id)
            if batch_without_picking_type:
                picking = self.picking_ids and self.picking_ids[0]
                batch_without_picking_type.picking_type_id = picking.picking_type_id.id
        if 'user_id' in vals:
            self.picking_ids.assign_batch_user(vals['user_id'])
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_done(self):
        if any(batch.state == 'done' for batch in self):
            raise UserError(_("You cannot delete Done batch transfers."))

    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Sanity checks, confirm the pickings and mark the batch as confirmed."""
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("You have to set some pickings to batch."))
        self.picking_ids.action_confirm()
        self._check_company()
        self.state = 'in_progress'
        return True

    def action_cancel(self):
        self.state = 'cancel'
        self.picking_ids = False
        return True

    def action_print(self):
        self.ensure_one()
        return self.env.ref('stock_picking_batch.action_report_picking_batch').report_action(self)

    def action_done(self):
        def has_no_quantity(picking):
            return all(not m.picked or m.product_uom.is_zero(m.quantity) for m in picking.move_ids if m.state not in ('done', 'cancel'))

        def is_empty(picking):
            return all(m.product_uom.is_zero(m.quantity) for m in picking.move_ids if m.state not in ('done', 'cancel'))

        self.ensure_one()
        self._check_company()
        # Empty 'assigned' or 'waiting for another operation' pickings will be removed from the batch when it is validated.
        pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
        empty_waiting_pickings = self.mapped('picking_ids').filtered(lambda p: (p.state in ('waiting', 'confirmed') and has_no_quantity(p)) or (p.state == 'assigned' and is_empty(p)))
        pickings = pickings - empty_waiting_pickings

        empty_pickings = pickings.filtered(has_no_quantity)

        # Run sanity_check as a batch and ignore the one in button_validate() since it is done here.
        pickings._sanity_check(separate_pickings=False)
        context = {
            'skip_sanity_check': True,   # Skip sanity_check in pickings button_validate()
            'pickings_to_detach': empty_waiting_pickings.ids,  # Remove 'waiting' pickings from the batch
            'batches_to_validate': self.ids,  # Skip current batch in auto_wave
        }
        if len(empty_pickings) != len(pickings):
            # If some pickings are at least partially done, other pickings (empty & waiting) will be removed from batch without being cancelled in case of no backorder
            pickings = pickings - empty_pickings
            context['pickings_to_detach'] = context['pickings_to_detach'] + empty_pickings.ids

        for picking in pickings:
            picking.message_post(
                body=Markup("<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.batch>%s</a>") % (
                    _("Transferred by"),
                    _("Batch Transfer"),
                    picking.batch_id.id,
                    picking.batch_id.name))

        if empty_waiting_pickings:
            self.message_post(body=_(
                "%s was removed from the batch, no quantity processed",
                Markup(', ').join([picking._get_html_link() for picking in empty_waiting_pickings])
            ))

        return pickings.with_context(**context).button_validate()

    def action_assign(self):
        self.ensure_one()
        self.picking_ids.action_assign()

    def action_put_in_pack(self, *, package_id=False, package_type_id=False, package_name=False):
        """ Action to put move lines with 'Done' quantities into a new pack
        This method follows same logic to stock.picking.
        """
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            return self.move_line_ids.action_put_in_pack(package_id=package_id, package_type_id=package_type_id, package_name=package_name)

    def action_view_reception_report(self):
        action = self.picking_ids[0].action_view_reception_report()
        action['context'] = {'default_picking_ids': self.picking_ids.ids}
        return action

    def action_open_label_layout(self):
        if self.env.user.has_group('stock.group_production_lot') and self.move_line_ids.lot_id:
            view = self.env.ref('stock.picking_label_type_form')
            return {
                'name': _('Choose Type of Labels To Print'),
                'type': 'ir.actions.act_window',
                'res_model': 'picking.label.type',
                'views': [(view.id, 'form')],
                'target': 'new',
                'context': {'default_picking_ids': self.picking_ids.ids},
            }
        view = self.env.ref('stock.product_label_layout_form_picking')
        return {
            'name': _('Choose Labels Layout'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.label.layout',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_product_ids': self.move_line_ids.product_id.ids,
                'default_move_ids': self.move_ids.ids,
                'default_move_quantity': 'move'},
        }

    def action_merge(self):
        if not self:
            return
        if len(self) < 2:
            raise UserError(self.env._('Please select at least two batch/wave transfers to merge.'))
        if len(self.picking_type_id) > 1:
            raise UserError(_('Batch/Wave transfers with different operation types cannot be merged.'))
        if len(set(self.mapped('is_wave'))) > 1:
            raise UserError(_('Batch transfers cannot be merged with wave transfers and vice versa.'))
        if len(set(self.mapped('state'))) > 1:
            raise UserError(_('Batch/Wave transfers with different states cannot be merged.'))
        if self[0].state in ['done', 'cancel']:
            raise UserError(_('You cannot merge done or cancelled batch/wave transfers.'))

        target_batch = self[:1]
        other_batches = self[1:]
        earliest_batch = self.filtered(lambda b: b.scheduled_date).sorted(key=lambda b: b.scheduled_date)[0]
        merged_batch_vals = earliest_batch._get_merged_batch_vals()
        target_batch.move_line_ids |= other_batches.move_line_ids
        target_batch.picking_ids |= other_batches.picking_ids
        target_batch.write(merged_batch_vals)
        other_batches.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch/Wave transfers have been merged into the following transfer'),
                'message': '%s',
                'links': [{
                    'label': target_batch.name,
                    'url': f"/odoo/action-stock_picking_batch.{'action_picking_tree_wave' if target_batch.is_wave else 'stock_picking_batch_action'}/{target_batch.id}",
                }],
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_batch_detailed_operations(self):
        self.ensure_one()
        view_id = self.env.ref('stock_picking_batch.view_move_line_tree').id
        return {
            'name': _('Detailed Operations'),
            'view_mode': 'list',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'views': [(view_id, 'list')],
            'domain': [('id', 'in', self.picking_ids.move_line_ids.ids)],
            'context': {
                'default_company_id': self.company_id.id,
                'default_picking_id': self.picking_ids and self.picking_ids[0].id or False,
                'picking_ids': self.picking_ids.ids,
                'show_lots_text': self.show_lots_text,
                'picking_code': self.picking_type_code,
                'create': self.state not in ('done', 'cancel'),
            }
        }

    def action_see_packages(self):
        self.ensure_one()
        if self.state == 'done':
            return {
                'name': self.env._("Packages"),
                'res_model': 'stock.package.history',
                'view_mode': 'list',
                'views': [(False, 'list')],
                'type': 'ir.actions.act_window',
                'domain': [('picking_ids', 'in', self.picking_ids.ids)],
                'context': {
                    'search_default_main_packages': True,
                }
            }

        return {
            'name': self.env._("Packages"),
            'res_model': 'stock.package',
            'view_mode': 'list,kanban,form',
            'views': [(self.env.ref('stock.stock_package_view_list_editable').id, 'list'), (False, 'kanban'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('picking_ids', 'in', self.picking_ids.ids)],
            'context': {
                'picking_ids': self.picking_ids.ids,
                'location_id': self.picking_ids[:1].location_id.id,
                'can_add_entire_packs': self.picking_type_code != 'incoming',
                'search_default_main_packages': True,
            },
        }

    # -------------------------------------------------------------------------
    # Miscellaneous
    # -------------------------------------------------------------------------
    @api.model
    def _prepare_name(self, picking_type, sequence_code, company_id):
        sequence_prefix, sequence_number = (self.env['ir.sequence'].with_company(company_id).next_by_code(sequence_code) or '/').split('/')
        return f"{sequence_prefix}/{picking_type.sequence_code}/{sequence_number}"

    def _sanity_check(self):
        for batch in self:
            if not batch.picking_ids <= batch.allowed_picking_ids:
                erroneous_pickings = batch.picking_ids - batch.allowed_picking_ids
                raise UserError(_(
                    "The following transfers cannot be added to batch transfer %(batch)s. "
                    "Please check their states and operation types.\n\n"
                    "Incompatibilities: %(incompatible_transfers)s",
                    batch=batch.name,
                    incompatible_transfers=erroneous_pickings.mapped('name')))

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return self.env.ref('stock_picking_batch.mt_batch_state')
        return super()._track_subtype(init_values)

    def _is_picking_auto_mergeable(self, picking):
        """ Verifies if a picking can be safely inserted into the batch without violating auto_batch_constrains.
        """
        res = True
        if self.picking_type_id.batch_max_lines:
            res = res and (len(self.move_ids) + len(picking.move_ids) <= self.picking_type_id.batch_max_lines)
        if self.picking_type_id.batch_max_pickings:
            res = res and (len(self.picking_ids) + 1 <= self.picking_type_id.batch_max_pickings)
        return res

    def _is_line_auto_mergeable(self, num_of_moves=False, num_of_pickings=False, weight=False):
        """ Verifies if a line can be safely inserted into the wave without violating auto_batch_constrains.
        """
        self.ensure_one()
        res = True
        if num_of_moves:
            res = res and self._are_moves_auto_mergeable(num_of_moves)
        if num_of_pickings:
            res = res and self._are_pickings_auto_mergeable(num_of_pickings)
        return res

    def _are_moves_auto_mergeable(self, num_of_moves):
        self.ensure_one()
        res = True
        if self.picking_type_id.batch_max_lines:
            res = res and (len(self.move_ids) + num_of_moves <= self.picking_type_id.batch_max_lines)
        return res

    def _are_pickings_auto_mergeable(self, num_of_pickings):
        self.ensure_one()
        res = True
        if self.picking_type_id.batch_max_pickings:
            res = res and (len(self.picking_ids) + num_of_pickings <= self.picking_type_id.batch_max_pickings)
        return res

    def _get_merged_batch_vals(self):
        self.ensure_one()
        return {
            'user_id': self.user_id.id,
            'description': self.description,
            'scheduled_date': self.scheduled_date,
        }
