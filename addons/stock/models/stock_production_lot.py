# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import findall as regex_findall
from re import split as regex_split

import operator as py_operator

from odoo.tools.misc import attrgetter
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne
}


class ProductionLot(models.Model):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lot/Serial'
    _check_company_auto = True
    _order = 'name, id'

    name = fields.Char(
        'Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True, help="Unique Lot/Serial Number", index=True)
    ref = fields.Char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's lot/serial number")
    product_id = fields.Many2one(
        'product.product', 'Product', index=True,
        domain=lambda self: self._domain_product_id(), required=True, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_id.uom_id', store=True)
    quant_ids = fields.One2many('stock.quant', 'lot_id', 'Quants', readonly=True)
    product_qty = fields.Float('Quantity', compute='_product_qty', search='_search_product_qty')
    note = fields.Html(string='Description')
    display_complete = fields.Boolean(compute='_compute_display_complete')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    delivery_ids = fields.Many2many('stock.picking', compute='_compute_delivery_ids', string='Transfers')
    delivery_count = fields.Integer('Delivery order count', compute='_compute_delivery_ids')
    last_delivery_partner_id = fields.Many2one('res.partner', compute='_compute_last_delivery_partner_id')

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

        lot_names = []
        for i in range(0, count):
            lot_names.append('%s%s%s' % (
                prefix,
                str(initial_number + i).zfill(padding),
                suffix
            ))
        return lot_names

    @api.model
    def _get_next_serial(self, company, product):
        """Return the next serial number to be attributed to the product."""
        if product.tracking != "none":
            last_serial = self.env['stock.production.lot'].search(
                [('company_id', '=', company.id), ('product_id', '=', product.id)],
                limit=1, order='id DESC')
            if last_serial:
                return self.env['stock.production.lot'].generate_lot_names(last_serial.name, 2)[1]
        return False

    @api.model
    def _get_new_serial(self, company, product):
        if product.tracking == 'lot':
            name = self.env['ir.sequence'].next_by_code('stock.lot.serial')
            exist_lot = self.env['stock.production.lot'].search([
                ('product_id', '=', product.id),
                ('company_id', '=', company.id),
                ('name', '=', name),
            ], limit=1)
            if exist_lot:
                return self.env['stock.production.lot']._get_next_serial(company, product)
            return name

        return self.env['stock.production.lot']._get_next_serial(company, product) or self.env['ir.sequence'].next_by_code('stock.lot.serial')

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('company_id', 'in', self.company_id.ids),
                  ('name', 'in', self.mapped('name'))]
        fields = ['company_id', 'product_id', 'name']
        groupby = ['company_id', 'product_id', 'name']
        records = self.read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(rec['product_id'][0]).display_name
                error_message_lines.append(_(" - Product: %s, Serial Number: %s", product_name, rec['name']))
        if error_message_lines:
            raise ValidationError(_('The combination of serial number and product must be unique across a company.\nFollowing combination contains duplicates:\n') + '\n'.join(error_message_lines))

    def _domain_product_id(self):
        domain = [
            "('tracking', '!=', 'none')",
            "('type', '=', 'product')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        return '[' + ', '.join(domain) + ']'

    def _check_create(self):
        active_picking_id = self.env.context.get('active_picking_id', False)
        if active_picking_id:
            picking_id = self.env['stock.picking'].browse(active_picking_id)
            if picking_id and not picking_id.picking_type_id.use_create_lots:
                raise UserError(_('You are not allowed to create a lot or serial number with this operation type. To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers".'))

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

    @api.model_create_multi
    def create(self, vals_list):
        self._check_create()
        return super(ProductionLot, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def write(self, vals):
        if 'company_id' in vals:
            for lot in self:
                if lot.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'product_id' in vals and any(vals['product_id'] != lot.product_id.id for lot in self):
            move_lines = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('product_id', '!=', vals['product_id'])])
            if move_lines:
                raise UserError(_(
                    'You are not allowed to change the product linked to a serial or lot number '
                    'if some stock moves have already been created with that number. '
                    'This would lead to inconsistencies in your stock.'
                ))
        return super(ProductionLot, self).write(vals)

    def copy(self, default=None):
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("(copy of) %s", self.name)
        return super().copy(default)

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
        lots_w_quants = self.env['stock.quant'].read_group(domain=domain, fields=['quantity:sum'], groupby=['lot_id'])
        ids = []
        lot_ids_w_qty = []
        for lot_w_quants in lots_w_quants:
            if OPERATORS['='](lot_w_quants['quantity'], 0.0):
                continue
            lot_id = lot_w_quants['lot_id'][0]
            lot_ids_w_qty.append(lot_id)
            if OPERATORS[operator](lot_w_quants['quantity'], value):
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
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
        return self.env['stock.quant']._get_quants_action()

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
                'view_mode': 'tree,form'
            })
        return action

    def _find_delivery_ids_by_lot(self, lot_path=None, delivery_by_lot=None):
        if lot_path is None:
            lot_path = set()
        domain = [
            ('lot_id', 'in', self.ids),
            ('state', '=', 'done'),
            '|', ('picking_code', '=', 'outgoing'), ('produce_line_ids', '!=', False)
        ]
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

                # delivery_ids = self._find_delivery_ids(moves_by_lot[lot.id])
            delivery_by_lot[lot.id] = list(delivery_ids)
        return delivery_by_lot
