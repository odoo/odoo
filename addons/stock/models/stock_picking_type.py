import json
from ast import literal_eval
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.translate import mark_as_copy


PRODUCT_LABEL_BARCODE_FORMATS = [
    ('barcode', 'Barcode'),
    ('qr', 'QR'),
]

PRODUCT_LABEL_SHEET_FORMATS = [
    ('dymo', 'Dymo'),
    ('2x7', '2 x 7'),
    ('4x7', '4 x 7'),
    ('4x12', '4 x 12'),
]

PRODUCT_LABEL_ZPL_TEMPLATES = [
    ('normal', 'ZPL Labels - Normal'),
    ('small', 'ZPL Labels - Small'),
    ('alternative', 'ZPL Labels - Alternative'),
    ('jewelry', 'ZPL Labels - Jewelry'),
]

PRODUCT_LABEL_FORMAT_VARIANTS = [
    ('', ''),
    ('_price', ', with price'),
    ('_price_packaging', ', with price, with packaging'),
]

LOT_LABEL_FORMATS = [
    ('4x12_lots', '4 x 12 - One per lot/SN'),
    ('4x12_units', '4 x 12 - One per unit'),
    ('zpl_lots', 'ZPL Labels - One per lot/SN'),
    ('zpl_units', 'ZPL Labels - One per unit'),
]


class StockPickingType(models.Model):
    _name = 'stock.picking.type'
    _description = "Picking Type"
    _explanation = "Defines the type of stock operation (e.g., Receipts, Deliveries, Internal Transfers) and contains configuration for how these operations should behave in the warehouse."
    _order = 'is_favorite desc, sequence, id'
    _rec_names_search = ('name', 'warehouse_id.name')
    _check_company_auto = True

    name = fields.Char('Operation Type', required=True, translate=True, copy=mark_as_copy('name'))
    color = fields.Integer('Color')
    sequence = fields.Integer('Sequence', help="Used to order the 'All Operations' kanban view")
    sequence_id = fields.Many2one(
        'ir.sequence', 'Reference Sequence',
        check_company=True, copy=False)
    sequence_code = fields.Char('Sequence Prefix', related='sequence_id.prefix', readonly=False)
    default_location_src_id = fields.Many2one(
        'stock.location', 'Source Location', compute='_compute_default_location_src_id',
        check_company=True, store=True, readonly=False, precompute=True, required=True,
        help="This is the default source location when this operation is manually created. However, it is possible to change it afterwards or that the routes use another one by default.")
    default_location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location', compute='_compute_default_location_dest_id',
        check_company=True, store=True, readonly=False, precompute=True, required=True,
        help="This is the default destination location when this operation is manually created. However, it is possible to change it afterwards or that the routes use another one by default.")
    allocated_location_id = fields.Many2one(
        'stock.location', 'Location for allocation', check_company=True,
        domain="[('usage', '=', 'internal')]",
        help="Allow to define the location where allocated products should be sent."
    )
    code = fields.Selection([
        ('incoming', 'Receipt'),
        ('outgoing', 'Delivery'),
        ('internal', 'Internal Transfer')], 'Type of Operation', default='incoming', required=True)
    return_picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type for Returns',
        index='btree_not_null',
        check_company=True)
    show_entire_packs = fields.Boolean('Move Entire Packages', default=False, help="If ticked, packages to move will be directly displayed in Barcode instead of the products they contain")
    set_package_type = fields.Boolean('Set Package Type', default=False, help="If ticked, you will be able to select which package or package type to use in a put in pack")
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', compute='_compute_warehouse_id', store=True, readonly=False, ondelete='cascade',
        check_company=True)
    active = fields.Boolean('Active', default=True)
    use_create_lots = fields.Boolean(
        'Create New Lots/Serial Numbers', default=True,
        compute='_compute_use_create_lots', store=True, readonly=False,
        help="If this is checked only, it will suppose you want to create new Lots/Serial Numbers, so you can provide them in a text field. ")
    use_existing_lots = fields.Boolean(
        'Use Existing Lots/Serial Numbers', default=True,
        compute='_compute_use_existing_lots', store=True, readonly=False,
        help="If this is checked, you will be able to choose the Lots/Serial Numbers. You can also decide to not put lots in this operation type.  This means it will create stock with no lot or not put a restriction on the lot taken. ")
    print_label = fields.Boolean(
        'Generate Shipping Labels', compute="_compute_print_label", store=True, readonly=False,
        help="Check this box if you want to generate shipping label in this operation.")
    reservation_method = fields.Selection(
        [('at_confirm', 'At Confirmation'), ('manual', 'Manually'), ('by_date', 'Before scheduled date')],
        'Reservation Method', required=True, default='at_confirm',
        help="How products in transfers of this operation type should be reserved.")
    reservation_days_before = fields.Integer('Days', help="Maximum number of days before scheduled date that products should be reserved.")
    reservation_days_before_priority = fields.Integer('Days when starred', help="Maximum number of days before scheduled date that priority picking products should be reserved.")
    auto_show_allocation_report = fields.Boolean(
        "Show Allocation",
        help="If this checkbox is ticked, Odoo will automatically show the allocation report (if there are moves to allocate to) when validating.")
    auto_print_delivery_slip = fields.Boolean(
        "Auto Print Delivery Slip",
        help="If this checkbox is ticked, Odoo will automatically print the delivery slip of a picking when it is validated.")
    auto_print_return_slip = fields.Boolean(
        "Auto Print Return Slip",
        help="If this checkbox is ticked, Odoo will automatically print the return slip of a picking when it is validated.")

    auto_print_product_labels = fields.Boolean(
        "Auto Print Product Labels",
        help="If this checkbox is ticked, Odoo will automatically print the product labels of a picking when it is validated.")
    product_label_format = fields.Selection(
        selection='_get_product_label_format_selection',
        string="Product Label Format to auto-print",
        default='barcode_2x7_price',
    )
    auto_print_lot_labels = fields.Boolean(
        "Auto Print Lot/SN Labels",
        help="If this checkbox is ticked, Odoo will automatically print the lot/SN labels of a picking when it is validated.")
    lot_label_format = fields.Selection(
        selection='_get_lot_label_format_selection',
        string="Lot Label Format to auto-print", default='4x12_lots')
    auto_print_reception_report = fields.Boolean(
        "Auto Print Reception Report",
        help="If this checkbox is ticked, Odoo will automatically print the reception report of a picking when it is validated and has assigned moves.")
    auto_print_reception_report_labels = fields.Boolean(
        "Auto Print Reception Report Labels",
        help="If this checkbox is ticked, Odoo will automatically print the reception report labels of a picking when it is validated.")
    auto_print_packages = fields.Boolean(
        "Auto Print Packages",
        help="If this checkbox is ticked, Odoo will automatically print the packages and their contents of a picking when it is validated.")

    auto_print_package_label = fields.Boolean(
        "Auto Print Package Label",
        help="If this checkbox is ticked, Odoo will automatically print the package label when \"Put in Pack\" button is used.")
    package_label_to_print = fields.Selection(
        [('pdf', 'PDF'), ('zpl', 'ZPL')],
        "Package Label to Print", default='pdf')

    @api.model
    def _get_product_label_format_selection(self):
        selection = []
        for barcode_format, barcode_label in PRODUCT_LABEL_BARCODE_FORMATS:
            for print_format, print_label in PRODUCT_LABEL_SHEET_FORMATS:
                for value_suffix, label_suffix in PRODUCT_LABEL_FORMAT_VARIANTS:
                    selection.append((
                        f'{barcode_format}_{print_format}{value_suffix}',
                        f'{barcode_label} {print_label}{label_suffix}',
                    ))
            for zpl_template, zpl_label in PRODUCT_LABEL_ZPL_TEMPLATES:
                for value_suffix, label_suffix in PRODUCT_LABEL_FORMAT_VARIANTS:
                    selection.append((
                        f'{barcode_format}_zpl_{zpl_template}{value_suffix}',
                        f'{barcode_label} {zpl_label}{label_suffix}',
                    ))
        return selection

    @api.model
    def _get_lot_label_format_selection(self):
        return LOT_LABEL_FORMATS

    @api.model
    def _get_product_label_format_options(self, product_label_format):
        product_label_format = product_label_format or 'barcode_2x7_price'
        barcode_format, print_format, *options = product_label_format.split('_')
        zpl_template = 'normal'
        if print_format == 'zpl':
            zpl_template, *options = options
        return {
            'print_format': print_format,
            'barcode_format': barcode_format,
            'zpl_template': zpl_template,
            'with_price': 'price' in options,
            'print_packaging': 'packaging' in options,
        }

    count_picking_draft = fields.Integer(compute='_compute_picking_count')
    count_picking_ready = fields.Integer(compute='_compute_picking_count')
    count_picking = fields.Integer(compute='_compute_picking_count')
    count_picking_waiting = fields.Integer(compute='_compute_picking_count')
    count_picking_late = fields.Integer(compute='_compute_picking_count')
    count_picking_backorders = fields.Integer(compute='_compute_picking_count')
    hide_reservation_method = fields.Boolean(compute='_compute_hide_reservation_method')
    barcode = fields.Char('Barcode', copy=False)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    create_backorder = fields.Selection(
        [('ask', 'Ask'), ('always', 'Always'), ('never', 'Never')],
        'Create Backorder', required=True, default='ask',
        help="When validating a transfer:\n"
             " * Ask: users are asked to choose if they want to make a backorder for remaining products\n"
             " * Always: a backorder is automatically created for the remaining products\n"
             " * Never: remaining products are cancelled")
    show_picking_type = fields.Boolean(compute='_compute_show_picking_type')
    show_return_picking_type = fields.Boolean(compute='_compute_show_return_picking_type')

    picking_properties_definition = fields.PropertiesDefinition("Picking Properties")
    favorite_user_ids = fields.Many2many(
        'res.users', 'picking_type_favorite_user_rel', 'picking_type_id', 'user_id',
    )
    is_favorite = fields.Boolean(
        compute='_compute_is_favorite', inverse='_inverse_is_favorite', search='_search_is_favorite',
        compute_sql='_compute_sql_is_favorite',
        compute_sudo=True, string='Show Operation in Overview'
    )
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
    move_type = fields.Selection([
        ('direct', 'As soon as possible, with back orders'), ('one', 'When all products are ready')], 'Shipping Policy',
        default=lambda self: self.env.company.picking_policy, required=True,
        help="It specifies goods to be transferred partially or all at once")

    # ==========================================================================
    # Batch related fields
    # ==========================================================================
    count_picking_batch = fields.Integer(compute='_compute_picking_count')
    count_picking_wave = fields.Integer(compute='_compute_picking_count')
    auto_batch = fields.Boolean('Automatic Batches',
        help="Automatically put pickings into batches as they are confirmed when possible.")
    batch_group_by_partner = fields.Boolean('Contact', help="Automatically group batches by contacts.")
    batch_group_by_destination = fields.Boolean('Destination Country', help="Automatically group batches by destination country.")
    batch_group_by_src_loc = fields.Boolean('Group by Source Location',
        help="Automatically group batches by their source location.")
    batch_group_by_dest_loc = fields.Boolean('Group by Destination Location',
        help="Automatically group batches by their destination location.")
    wave_group_by_product = fields.Boolean('Product',
        help="Split transfers by product then group transfers that have the same product.")
    wave_group_by_category = fields.Boolean('Product Category',
        help="Split transfers by product category, then group transfers that have the same product category.")
    wave_category_ids = fields.Many2many('product.category',
        string='Wave Product Categories', help="Categories to consider when grouping waves.")
    wave_group_by_location = fields.Boolean('Location',
        help="Split transfers by defined locations, then group transfers with the same location.")
    wave_location_ids = fields.Many2many('stock.location',
        string='Wave Locations',
        help="Locations to consider when grouping waves.",
        domain="[('usage', '=', 'internal')]")
    batch_max_lines = fields.Integer("Maximum lines",
        help="A transfer will not be automatically added to batches that will exceed this number of lines if the transfer is added to it.\n"
             "Leave this value as '0' if no line limit.")
    batch_max_pickings = fields.Integer("Maximum transfers",
        help="A transfer will not be automatically added to batches that will exceed this number of transfers.\n"
             "Leave this value as '0' if no transfer limit.")
    batch_auto_confirm = fields.Boolean("Auto-confirm", default=True)
    batch_properties_definition = fields.PropertiesDefinition('Batch Properties')

    @api.constrains(lambda self: self._get_batch_group_by_keys() + ['auto_batch'])
    def _check_auto_batch_options(self):
        group_by_keys = self._get_batch_and_wave_group_by_keys()
        for picking_type in self:
            if not picking_type.auto_batch:
                continue
            if not any(picking_type[key] for key in group_by_keys):
                raise ValidationError(_("If the Automatic Batches feature is enabled, at least one 'Group by' option must be selected."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_id') and vals.get('sequence_code'):
                if vals.get('warehouse_id'):
                    wh = self.env['stock.warehouse'].browse(vals['warehouse_id'])
                    vals['sequence_id'] = self.env['ir.sequence'].sudo().create({
                        'name': _('%(warehouse)s Sequence %(code)s', warehouse=wh.name, code=vals['sequence_code']),
                        'padding': 5,
                        'company_id': wh.company_id.id,
                    }).id
                else:
                    vals['sequence_id'] = self.env['ir.sequence'].sudo().create({
                        'name': _('Sequence %(code)s', code=vals['sequence_code']),
                        'padding': 5,
                        'company_id': vals.get('company_id') or self.env.company.id,
                    }).id
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for picking, vals in zip(self, vals_list):
            if 'sequence_code' not in default and 'sequence_id' not in default:
                vals['sequence_code'] = _("%s (copy)", picking.sequence_code)
        return vals_list

    def write(self, vals):
        if 'company_id' in vals:
            for picking_type in self:
                if picking_type.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'sequence_code' in vals:
            for picking_type in self:
                if vals.get('sequence_id') is False:  # revert the sequence_id
                    vals['sequence_id'] = picking_type.sequence_id.id
                if picking_type.warehouse_id:
                    picking_type.sequence_id.sudo().write({
                        'name': _('%(warehouse)s Sequence %(code)s', warehouse=picking_type.warehouse_id.name, code=vals['sequence_code']),
                        'padding': 5,
                        'company_id': picking_type.warehouse_id.company_id.id,
                    })
                else:
                    picking_type.sequence_id.sudo().write({
                        'name': _('Sequence %(code)s', code=vals['sequence_code']),
                        'padding': 5,
                        'company_id': picking_type.env.company.id,
                    })
        if 'reservation_method' in vals:
            if vals['reservation_method'] == 'by_date':
                if picking_types := self.filtered(lambda p: p.reservation_method != 'by_date'):
                    domain = [('picking_type_id', 'in', picking_types.ids), ('state', 'in', ('draft', 'confirmed', 'waiting', 'partially_available'))]
                    group_by = ['picking_type_id']
                    aggregates = ['id:recordset']
                    for picking_type, moves in self.env['stock.move']._read_group(domain, group_by, aggregates):
                        common_days = vals.get('reservation_days_before') or picking_type.reservation_days_before
                        priority_days = vals.get('reservation_days_before_priority') or picking_type.reservation_days_before_priority
                        for move in moves:
                            move.reservation_date = fields.Date.to_date(move.date) - timedelta(days=priority_days if move.priority == '1' else common_days)
            else:
                if picking_types := self.filtered(lambda p: p.reservation_method == 'by_date'):
                    moves = self.env['stock.move'].search([('picking_type_id', 'in', picking_types.ids), ('state', 'not in', ('assigned', 'done', 'cancel'))])
                    moves.reservation_date = False

        return super().write(vals)

    @api.model
    def _search_is_favorite(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('favorite_user_ids', 'in', [self.env.uid])]

    def _compute_is_favorite(self):
        for picking_type in self:
            picking_type.is_favorite = self.env.user in picking_type.favorite_user_ids

    def _inverse_is_favorite(self):
        sudoed_self = self.sudo()
        to_fav = sudoed_self.filtered(
            lambda picking_type: self.env.user not in picking_type.favorite_user_ids
        )
        to_fav.write({'favorite_user_ids': [(4, self.env.uid)]})
        (sudoed_self - to_fav).write({'favorite_user_ids': [(3, self.env.uid)]})

    def _compute_sql_is_favorite(self, table):
        return SQL(
            "%s IN (SELECT picking_type_id FROM picking_type_favorite_user_rel WHERE user_id = %s)",
            table.id, self.env.uid,
        )

    @api.depends('code')
    def _compute_hide_reservation_method(self):
        for rec in self:
            rec.hide_reservation_method = rec.code == 'incoming'

    def _compute_picking_count(self):
        base_domain = Domain([('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)])
        # TODO (to check if it's not overkill): to avoid some `_read_group`:
        #   - `count_picking` could be the sum of `count_picking_waiting` and `count_picking_ready`;
        #   - We could compute some fields like we did for `count_picking_wave` and `count_picking_batch`
        #     by checking a field value (would be easy for `state` and `backorder_id`.)
        active_picking_states = ('assigned', 'waiting', 'confirmed')
        domains = {
            'count_picking_draft': Domain('state', '=', 'draft'),
            'count_picking_waiting': Domain('state', 'in', ('confirmed', 'waiting')),
            'count_picking_ready': Domain('state', '=', 'assigned'),
            'count_picking': Domain('state', 'in', active_picking_states),
            'count_picking_late': Domain([
                ('state', 'in', active_picking_states),
                '|',
                ('scheduled_date', '<', fields.Date.today()),
                ('has_deadline_issue', '=', True),
            ]),
            'count_picking_backorders': Domain([
                ('backorder_id', '!=', False),
                ('state', 'in', active_picking_states),
            ]),
        }
        for field_name, domain in domains.items():
            data = self.env['stock.picking']._read_group(
                Domain.AND([base_domain, domain]), ['picking_type_id'], ['__count'])
            count = {picking_type.id: count for picking_type, count in data}
            for record in self:
                record[field_name] = count.get(record.id, 0)

        if self.env.user.has_group('stock.group_stock_picking_batch'):
            data = self.env['stock.picking.batch']._read_group(
                base_domain, ['picking_type_id', 'is_wave'], ['__count'])
            count = {(picking_type.id, is_wave): count for picking_type, is_wave, count in data}
            for record in self:
                record.count_picking_wave = count.get((record.id, True), 0)
                record.count_picking_batch = count.get((record.id, False), 0)
        else:
            self.count_picking_batch, self.count_picking_wave = 0, 0

    @api.depends('warehouse_id')
    def _compute_display_name(self):
        """ Display 'Warehouse_name: PickingType_name' """
        for picking_type in self:
            if picking_type.warehouse_id:
                picking_type.display_name = f"{picking_type.warehouse_id.name}: {picking_type.name}"
            else:
                picking_type.display_name = picking_type.name

    @api.depends('code')
    def _compute_use_create_lots(self):
        for picking_type in self:
            if picking_type.code == 'incoming':
                picking_type.use_create_lots = True

    @api.depends('code')
    def _compute_use_existing_lots(self):
        for picking_type in self:
            if picking_type.code == 'outgoing':
                picking_type.use_existing_lots = True

    @api.model
    def _search_display_name(self, operator, value):
        # Try to reverse the `display_name` structure
        if operator == 'in':
            return Domain.OR(self._search_display_name('=', v) for v in value)
        if operator == 'not in':
            return NotImplemented
        parts = isinstance(value, str) and value.split(': ')
        if parts and len(parts) == 2:
            return Domain('warehouse_id.name', operator, parts[0]) & Domain('name', operator, parts[1])
        if operator == '=':
            operator = 'in'
            value = [value]
        return super()._search_display_name(operator, value)

    @api.depends('code')
    def _compute_default_location_src_id(self):
        for picking_type in self:
            if not picking_type.warehouse_id:
                self.env['stock.warehouse']._warehouse_redirect_warning()
            stock_location = picking_type.warehouse_id.lot_stock_id
            if picking_type.code == 'incoming':
                picking_type.default_location_src_id = self.env.ref('stock.stock_location_suppliers').id
            else:
                picking_type.default_location_src_id = stock_location.id

    @api.depends('code')
    def _compute_default_location_dest_id(self):
        for picking_type in self:
            if not picking_type.warehouse_id:
                self.env['stock.warehouse']._warehouse_redirect_warning()
            stock_location = picking_type.warehouse_id.lot_stock_id
            if picking_type.code == 'outgoing':
                picking_type.default_location_dest_id = self.env.ref('stock.stock_location_customers').id
            else:
                picking_type.default_location_dest_id = stock_location.id

    @api.depends('code')
    def _compute_print_label(self):
        for picking_type in self:
            if picking_type.code in ('incoming', 'internal'):
                picking_type.print_label = False
            elif picking_type.code == 'outgoing':
                picking_type.print_label = True

    @api.onchange('code')
    def _onchange_picking_code(self):
        if self.code == 'internal' and not self.env.user.has_group('stock.group_stock_multi_locations'):
            return {
                'warning': {
                    'message': _('You need to activate storage locations to be able to do internal operation types.')
                }
            }

    @api.depends('company_id')
    def _compute_warehouse_id(self):
        for picking_type in self:
            if picking_type.warehouse_id:
                continue
            if picking_type.company_id:
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', picking_type.company_id.id)], limit=1)
                picking_type.warehouse_id = warehouse

    @api.depends('code')
    def _compute_show_picking_type(self):
        for record in self:
            record.show_picking_type = record.code in ['incoming', 'outgoing', 'internal']

    @api.depends('code')
    def _compute_show_return_picking_type(self):
        for picking_type in self:
            picking_type.show_return_picking_type = picking_type.code in ['incoming', 'outgoing', 'internal']

    def _compute_kanban_dashboard_graph(self):
        grouped_records = self._get_aggregated_records_by_date()

        summaries = {}
        for picking_type_id, dates, data_series_name in grouped_records:
            summaries[picking_type_id] = {
                'data_series_name': data_series_name,
                'total_before': 0,
                'total_yesterday': 0,
                'total_today': 0,
                'total_day_1': 0,
                'total_day_2': 0,
                'total_after': 0,
            }
            for p_date in dates:
                date_category = self.env["stock.picking"].calculate_date_category(p_date)
                if date_category:
                    summaries[picking_type_id]['total_' + date_category] += 1

        self._prepare_graph_data(summaries)

    @api.onchange('sequence_code')
    def _onchange_sequence_code(self):
        if not self.sequence_code:
            return
        domain = [('sequence_code', '=', self.sequence_code), '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if self._origin.id:
            domain += [('id', '!=', self._origin.id)]
        picking_type = self.env['stock.picking.type'].search(domain, limit=1)
        if picking_type and picking_type.sequence_id != self.sequence_id:
            return {
                'warning': {
                    'message': _(
                        "This sequence prefix is already being used by another operation type. It is recommended that you select a unique prefix "
                        "to avoid issues and/or repeated reference values or assign the existing reference sequence to this operation type.")
                }
            }

    @api.model
    def action_redirect_to_barcode_installation(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("base.open_module_tree")
        action["context"] = dict(literal_eval(action["context"]), search_default_name="Barcode")
        return action

    def action_batch(self):
        action = self._get_action('stock.stock_picking_batch_action')
        if self.env.context.get("view_mode"):
            del action["mobile_view_mode"]
            del action["views"]
            action["view_mode"] = self.env.context["view_mode"]
        return action

    def action_wave(self):
        action = self._get_action('stock.action_picking_tree_wave')
        return action

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        context = {}

        if self:
            action['display_name'] = self.display_name
            context.update({
                'default_picking_type_id': self.id,
                'default_company_id': self.company_id.id,
            })
        else:
            allowed_company_ids = self.env.context.get('allowed_company_ids', [])
            if allowed_company_ids:
                context.update({
                    'default_company_id': allowed_company_ids[0],
                })

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        action['domain'] = [('picking_type_id', '=', self.id)]

        action['help'] = self.env['ir.ui.view']._render_template(
            'stock.help_message_template', {
                'picking_type_code': context.get('restricted_picking_type_code') or self.code,
            }
        )

        return action

    def get_action_picking_tree_late(self):
        return self._get_action('stock.action_picking_tree_late')

    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    def get_action_picking_tree_waiting(self):
        return self._get_action('stock.action_picking_tree_waiting')

    def get_action_picking_tree_ready(self):
        return self._get_action('stock.action_picking_tree_ready')

    def get_action_picking_type_moves_analysis(self):
        action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_move_action')
        action['domain'] = Domain.AND([
            action['domain'] or [], [('picking_type_id', '=', self.id)]
        ])
        return action

    def get_stock_picking_action_picking_type(self):
        if self.code == 'incoming':
            return self._get_action('stock.action_picking_tree_incoming')
        if self.code == 'outgoing':
            return self._get_action('stock.action_picking_tree_outgoing')
        if self.code == 'internal':
            return self._get_action('stock.action_picking_tree_internal')
        return self._get_action('stock.stock_picking_action_picking_type')

    def _get_aggregated_records_by_date(self):
        """
        Returns a list, each element containing 3 values:
        * picking type ID
        * list of date fields values of all pickings with that picking type
        * data series name, used to display it in the graph
        """
        records = self.env['stock.picking']._read_group(
            [
                ('picking_type_id', 'in', self.ids),
                ('state', 'in', ['assigned', 'waiting', 'confirmed'])
            ],
            ['picking_type_id'],
            ['scheduled_date' + ':array_agg'],
        )
        # Make sure that all picking type IDs are represented, even if empty
        picking_type_id_to_dates = {i: [] for i in self.ids}
        picking_type_id_to_dates.update({r[0].id: r[1] for r in records})
        return [(i, d, self.env._('Transfers')) for i, d in picking_type_id_to_dates.items()]

    def _prepare_graph_data(self, summaries):
        """
        Takes in summaries of picking types, each containing the name of the data
        series and categories to display with their corresponding stock picking counts.
        Converts each summary into data suitable for the dashboard graph and assigns
        that data to the corresponding picking type from `self`.

        If all values in a graph are 0, then they are assigned the "sample" type.
        """
        data_category_mapping = {
            'total_before': {'label': _('Before'), 'type': 'past'},
            'total_yesterday': {'label': _('Yesterday'), 'type': 'past'},
            'total_today': {'label': _('Today'), 'type': 'present'},
            'total_day_1': {'label': _('Tomorrow'), 'type': 'future'},
            'total_day_2': {'label': _('The day after tomorrow'), 'type': 'future'},
            'total_after': {'label': _('After'), 'type': 'future'},
        }

        for picking_type in self:
            picking_type_summary = summaries.get(picking_type.id)
            # Graph is empty if all its "total_*" values are 0
            empty = all(picking_type_summary[k] == 0 for k in data_category_mapping)
            graph_data = [{
                'key': _('Sample data') if empty else picking_type_summary['data_series_name'],
                # Passing the picking type ID allows for a redirection after clicking
                'picking_type_id': None if empty else picking_type.id,
                'values': [
                    dict(v, value=picking_type_summary[k], type='sample' if empty else v['type'])
                    for k, v in data_category_mapping.items()
                ],
            }]
            picking_type.kanban_dashboard_graph = json.dumps(graph_data)

    def _get_code_report_name(self):
        self.ensure_one()
        code_names = {
            'outgoing': _('Delivery Note'),
            'incoming': _('Goods Receipt Note'),
            'internal': _('Internal Move'),
        }
        return code_names.get(self.code)

    # ===== Batch business methods =====

    def _is_auto_batch_grouped(self):
        self.ensure_one()
        return self.auto_batch and any(self[key] for key in self._get_batch_group_by_keys())

    def _is_auto_wave_grouped(self):
        self.ensure_one()
        return self.auto_batch and any(self[key] for key in self._get_wave_group_by_keys())

    @api.model
    def _get_batch_group_by_keys(self):
        return ['batch_group_by_destination', 'batch_group_by_src_loc', 'batch_group_by_dest_loc', 'batch_group_by_partner']

    @api.model
    def _get_wave_group_by_keys(self):
        return ['wave_group_by_category', 'wave_group_by_location', 'wave_group_by_product']

    @api.model
    def _get_batch_and_wave_group_by_keys(self):
        return self._get_batch_group_by_keys() + self._get_wave_group_by_keys()
