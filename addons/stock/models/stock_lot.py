# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator as py_operator
from operator import attrgetter
from re import findall as regex_findall, split as regex_split

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne
}


class StockLot(models.Model):
    _name = 'stock.lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lot/Serial'
    _check_company_auto = True
    _order = 'name, id'

    @api.model
    def default_get(self, fields_list):
        context = dict(self.env.context)
        # We always want the company_id to be computed, regardless of where it's been created.
        context.pop('default_company_id', False)
        return super(StockLot, self.with_context(context)).default_get(fields_list)

    def _read_group_location_id(self, locations, domain):
        partner_locations = locations.search([('usage', 'in', ('customer', 'supplier'))])
        return partner_locations + locations.warehouse_id.search([]).lot_stock_id

    name = fields.Char(
        'Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True, help="Unique Lot/Serial Number", index='trigram')
    ref = fields.Char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's lot/serial number")
    product_id = fields.Many2one(
        'product.product', 'Product', index=True,
        domain=("[('tracking', '!=', 'none'), ('is_storable', '=', True)] +"
            " ([('product_tmpl_id', '=', context['default_product_tmpl_id'])] if context.get('default_product_tmpl_id') else [])"),
        required=True, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_id.uom_id', store=True)
    quant_ids = fields.One2many('stock.quant', 'lot_id', 'Quants', readonly=True)
    product_qty = fields.Float('On Hand Quantity', compute='_product_qty', search='_search_product_qty')
    note = fields.Html(string='Description')
    display_complete = fields.Boolean(compute='_compute_display_complete')
    company_id = fields.Many2one('res.company', 'Company', index=True, store=True, readonly=False, compute='_compute_company_id')
    delivery_ids = fields.Many2many('stock.picking', compute='_compute_delivery_ids', string='Transfers')
    delivery_count = fields.Integer('Delivery order count', compute='_compute_delivery_ids')
    last_delivery_partner_id = fields.Many2one('res.partner', compute='_compute_last_delivery_partner_id')
    lot_properties = fields.Properties('Properties', definition='product_id.lot_properties_definition', copy=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_single_location', store=True, readonly=False,
        inverse='_set_single_location', domain="[('usage', '!=', 'view')]", group_expand='_read_group_location_id')

    @api.model
    def generate_lot_names(self, first_lot, count):
        """Generate `lot_names` from a string."""
        # We look if the first lot contains at least one digit.
        caught_initial_number = regex_findall(r"\d+", first_lot)
        if not caught_initial_number:
            return self.generate_lot_names(first_lot + "0", count)
        # We base the series on the last number found in the base lot.
        initial_number = caught_initial_number[-1]
        padding = len(initial_number)
        # We split the lot name to get the prefix and suffix.
        splitted = regex_split(initial_number, first_lot)
        # initial_number could appear several times, e.g. BAV023B00001S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)

        return [{
            'lot_name': '%s%s%s' % (prefix, str(initial_number + i).zfill(padding), suffix),
        } for i in range(0, count)]

    @api.model
    def _get_next_serial(self, company, product):
        """Return the next serial number to be attributed to the product."""
        if product.tracking != "none":
            last_serial = self.env['stock.lot'].search(
                ['|', ('company_id', '=', company.id), ('company_id', '=', False), ('product_id', '=', product.id)],
                limit=1, order='id DESC')
            if last_serial:
                return self.env['stock.lot'].generate_lot_names(last_serial.name, 2)[1]['lot_name']
        return False

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('name', 'in', self.mapped('name'))]
        groupby = ['company_id', 'product_id', 'name']
        if any(not lot.company_id for lot in self):
            # We need to check across other companies to not have duplicates between 'no-company' and a company.
            self = self.sudo()
        records = self._read_group(domain, groupby, ['__count'], order='company_id DESC')
        error_message_lines = set()
        cross_lots = {}
        for company, product, name, count in records:
            if not company:
                cross_lots[(product, name)] = count
            # For company-specific lots, we check that there is no duplicate with 'no-company' lots, but NOT between specific-company ones.
            if (company and (cross_lots.get((product, name), 0) + count) > 1) or count > 1:
                error_message_lines.add(_(" - Product: %(product)s, Lot/Serial Number: %(lot)s", product=product.display_name, lot=name))
        if error_message_lines:
            raise ValidationError(
                _(
                    "The combination of lot/serial number and product must be unique within a company including when no company is defined.\nThe following combinations contain duplicates:\n%(error_lines)s",
                    error_lines="\n".join(error_message_lines),
                ),
            )

    def _check_create(self):
        active_picking_id = self.env.context.get('active_picking_id', False)
        if active_picking_id:
            picking_id = self.env['stock.picking'].browse(active_picking_id)
            if picking_id and not picking_id.picking_type_id.use_create_lots:
                raise UserError(_('You are not allowed to create a lot or serial number with this operation type. To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers".'))

    @api.depends('product_id.company_id')
    def _compute_company_id(self):
        for lot in self:
            if self.env.company in lot.product_id.company_id.all_child_ids and lot.product_id.company_id not in self.env.companies:
                lot.company_id = self.env.company
            else:
                lot.company_id = lot.product_id.company_id

    @api.depends('name')
    def _compute_display_complete(self):
        """ Defines if we want to display all fields in the stock.production.lot form view.
        It will if the record exists (`id` set) or if we precised it into the context.
        This compute depends on field `name` because as it has always a default value, it'll be
        always triggered.
        """
        for prod_lot in self:
            prod_lot.display_complete = prod_lot.id or self._context.get('display_complete')

    def _compute_delivery_ids(self):
        delivery_ids_by_lot = self._find_delivery_ids_by_lot()
        for lot in self:
            lot.delivery_ids = delivery_ids_by_lot[lot.id]
            lot.delivery_count = len(lot.delivery_ids)

    def _compute_last_delivery_partner_id(self):
        serial_products = self.filtered(lambda l: l.product_id.tracking == 'serial')
        delivery_ids_by_lot = serial_products._find_delivery_ids_by_lot()
        (self - serial_products).last_delivery_partner_id = False
        for lot in serial_products:
            if lot.product_id.tracking == 'serial' and len(delivery_ids_by_lot[lot.id]) > 0:
                lot.last_delivery_partner_id = self.env['stock.picking'].browse(delivery_ids_by_lot[lot.id]).sorted(key='date_done', reverse=True)[0].partner_id
            else:
                lot.last_delivery_partner_id = False

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _compute_single_location(self):
        for lot in self:
            quants = lot.quant_ids.filtered(lambda q: q.quantity > 0)
            lot.location_id = quants.location_id if len(quants.location_id) == 1 else False

    def _set_single_location(self):
        quants = self.quant_ids.filtered(lambda q: q.quantity > 0)
        if len(quants.location_id) == 1:
            unpack = len(quants.package_id.quant_ids) > 1
            quants.move_quants(location_dest_id=self.location_id, message=_("Lot/Serial Number Relocated"), unpack=unpack)
        elif len(quants.location_id) > 1:
            raise UserError(_('You can only move a lot/serial to a new location if it exists in a single location.'))

    @api.model_create_multi
    def create(self, vals_list):
        lot_product_ids =  {val.get('product_id') for val in vals_list} | {self.env.context.get('default_product_id')}
        self.with_context(lot_product_ids=lot_product_ids)._check_create()
        return super(StockLot, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def write(self, vals):
        if 'company_id' in vals:
            for lot in self:
                if lot.location_id.company_id and vals['company_id'] and lot.location_id.company_id.id != vals['company_id']:
                    raise UserError(_("You cannot change the company of a lot/serial number currently in a location belonging to another company."))
        if 'product_id' in vals and any(vals['product_id'] != lot.product_id.id for lot in self):
            move_lines = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('product_id', '!=', vals['product_id'])])
            if move_lines:
                raise UserError(_(
                    'You are not allowed to change the product linked to a serial or lot number '
                    'if some stock moves have already been created with that number. '
                    'This would lead to inconsistencies in your stock.'
                ))
        return super().write(vals)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for lot, vals in zip(self, vals_list):
                vals['name'] = _("(copy of) %s", lot.name)
        return vals_list

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _product_qty(self):
        for lot in self:
            # We only care for the quants in internal or transit locations.
            quants = lot.quant_ids.filtered(lambda q: q.location_id.usage == 'internal' or (q.location_id.usage == 'transit' and q.location_id.company_id))
            lot.product_qty = sum(quants.mapped('quantity'))

    def _search_product_qty(self, operator, value):
        if operator not in OPERATORS:
            raise UserError(_("Invalid domain operator %s", operator))
        if not isinstance(value, (float, int)):
            raise UserError(_("Invalid domain right operand '%s'. It must be of type Integer/Float", value))
        domain = [
            ('lot_id', '!=', False),
            '|', ('location_id.usage', '=', 'internal'),
            '&', ('location_id.usage', '=', 'transit'), ('location_id.company_id', '!=', False)
        ]
        lots_w_qty = self.env['stock.quant']._read_group(domain=domain, groupby=['lot_id'], aggregates=['quantity:sum'], having=[('quantity:sum', '!=', 0)])
        ids = []
        lot_ids_w_qty = []
        for lot, quantity_sum in lots_w_qty:
            lot_id = lot.id
            lot_ids_w_qty.append(lot_id)
            if OPERATORS[operator](quantity_sum, value):
                ids.append(lot_id)
        if value == 0.0 and operator == '=':
            return [('id', 'not in', lot_ids_w_qty)]
        if value == 0.0 and operator == '!=':
            return [('id', 'in', lot_ids_w_qty)]
        # check if we need include zero values in result
        include_zero = (
            value < 0.0 and operator in ('>', '>=') or
            value > 0.0 and operator in ('<', '<=') or
            value == 0.0 and operator in ('>=', '<=')
        )
        if include_zero:
            return ['|', ('id', 'in', ids), ('id', 'not in', lot_ids_w_qty)]
        return [('id', 'in', ids)]

    def action_lot_open_quants(self):
        self = self.with_context(search_default_lot_id=self.id, create=False)
        if self.env.user.has_group('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
        return self.env['stock.quant'].action_view_quants()

    def action_lot_open_transfers(self):
        self.ensure_one()

        action = {
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window'
        }
        if len(self.delivery_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.delivery_ids[0].id
            })
        else:
            action.update({
                'name': _("Delivery orders of %s", self.display_name),
                'domain': [('id', 'in', self.delivery_ids.ids)],
                'view_mode': 'list,form'
            })
        return action

    @api.model
    def _get_outgoing_domain(self):
        return [
            '|',
            ('picking_code', '=', 'outgoing'),
            ('produce_line_ids', '!=', False),
        ]

    def _find_delivery_ids_by_lot(self, lot_path=None, delivery_by_lot=None):
        if lot_path is None:
            lot_path = set()
        domain = [
            ('lot_id', 'in', self.ids),
            ('state', '=', 'done'),
        ]
        domain_restriction = self._get_outgoing_domain()
        domain = expression.AND([domain, domain_restriction])
        move_lines = self.env['stock.move.line'].search(domain)
        moves_by_lot = {
            lot_id: {'producing_lines': set(), 'barren_lines': set()}
            for lot_id in move_lines.lot_id.ids
        }
        for line in move_lines:
            if line.produce_line_ids:
                moves_by_lot[line.lot_id.id]['producing_lines'].add(line.id)
            else:
                moves_by_lot[line.lot_id.id]['barren_lines'].add(line.id)
        if delivery_by_lot is None:
            delivery_by_lot = dict()
        for lot in self:
            delivery_ids = set()

            if moves_by_lot.get(lot.id):
                producing_move_lines = self.env['stock.move.line'].browse(moves_by_lot[lot.id]['producing_lines'])
                barren_move_lines = self.env['stock.move.line'].browse(moves_by_lot[lot.id]['barren_lines'])

                if producing_move_lines:
                    lot_path.add(lot.id)
                    next_lots = producing_move_lines.produce_line_ids.lot_id.filtered(lambda l: l.id not in lot_path)
                    next_lots_ids = set(next_lots.ids)
                    # If some producing lots are in lot_path, it means that they have been previously processed.
                    # Their results are therefore already in delivery_by_lot and we add them to delivery_ids directly.
                    delivery_ids.update(*(delivery_by_lot.get(lot_id, []) for lot_id in (producing_move_lines.produce_line_ids.lot_id - next_lots).ids))

                    for lot_id, delivery_ids_set in next_lots._find_delivery_ids_by_lot(lot_path=lot_path, delivery_by_lot=delivery_by_lot).items():
                        if lot_id in next_lots_ids:
                            delivery_ids.update(delivery_ids_set)
                delivery_ids.update(barren_move_lines.picking_id.ids)

            delivery_by_lot[lot.id] = list(delivery_ids)
        return delivery_by_lot
