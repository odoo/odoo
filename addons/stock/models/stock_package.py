# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import groupby
from odoo.tools.barcode import check_barcode_encoding
from odoo.tools.float_utils import float_is_zero


class StockPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.package'
    _description = "Packages"
    _order = 'name'

    name = fields.Char(
        'Package Reference', copy=False, index='trigram', required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.package') or self.env._('Unknown Pack'))
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    package_type_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=False, store=True)
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_owner_id', search='_search_owner',
        readonly=True, compute_sudo=True)
    package_use = fields.Selection([
        ('disposable', 'Disposable Box'),
        ('reusable', 'Reusable Box'),
        ], string='Package Use', default='disposable', required=True,
        help="""Reusable boxes are used for batch picking and emptied afterwards to be reused. In the barcode application, scanning a reusable box will add the products in this box.
        Disposable boxes aren't reused, when scanning a disposable box in the barcode application, the contained products are added to the transfer.""")
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")
    valid_sscc = fields.Boolean('Package name is valid SSCC', compute='_compute_valid_sscc')
    pack_date = fields.Date('Pack Date', default=fields.Date.today)

    @api.depends('name', 'package_type_id.packaging_length', 'package_type_id.width', 'package_type_id.height')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        packages_to_process_ids = []
        for package in self:
            if package.env.context.get('formatted_display_name') and package.package_type_id and package.package_type_id.packaging_length and package.package_type_id.width and package.package_type_id.height:
                package.display_name = f"{package.name}\t--{package.package_type_id.packaging_length} x {package.package_type_id.width} x {package.package_type_id.height}--"
            else:
                packages_to_process_ids.append(package.id)
        if packages_to_process_ids:
            super(StockPackage, self.env['stock.package'].browse(packages_to_process_ids))._compute_display_name()

    @api.depends('quant_ids.location_id', 'quant_ids.company_id')
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.quant_ids.filtered(lambda q: q.product_uom_id.compare(q.quantity, 0) > 0)
            if quants:
                package.location_id = quants[0].location_id
                if all(q.company_id == quants[0].company_id for q in package.quant_ids):
                    package.company_id = quants[0].company_id

    @api.depends('quant_ids.owner_id')
    def _compute_owner_id(self):
        for package in self:
            package.owner_id = False
            if package.quant_ids and all(
                q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids
            ):
                package.owner_id = package.quant_ids[0].owner_id

    @api.depends('name')
    def _compute_valid_sscc(self):
        self.valid_sscc = False
        for package in self:
            if package.name:
                package.valid_sscc = check_barcode_encoding(package.name, 'sscc')

    def _search_owner(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain('quant_ids.owner_id', operator, value)

    def write(self, vals):
        if 'location_id' in vals:
            if not vals['location_id']:
                raise UserError(self.env._('Cannot remove the location of a non empty package'))
            if any(not pack.quant_ids for pack in self):
                raise UserError(self.env._('Cannot move an empty package'))
            # create a move from the old location to new location
            location_dest_id = self.env['stock.location'].browse(vals['location_id'])
            quant_to_move = self.quant_ids.filtered(lambda q: q.quantity > 0)
            quant_to_move.move_quants(location_dest_id, message=self.env._('Package manually relocated'))
        return super().write(vals)

    def unpack(self):
        self.quant_ids.move_quants(message=self.env._("Quantities unpacked"), unpack=True)
        # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
        # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
        self.quant_ids._quant_tasks()

    def action_view_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        domain = ['|', ('result_package_id', 'in', self.ids), ('package_id', 'in', self.ids)]
        pickings = self.env['stock.move.line'].search(domain).mapped('picking_id')
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    def _check_move_lines_map_quant(self, move_lines):
        """ This method checks that all product (quants) of self (package) are well present in the `move_line_ids`. """
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        def _keys_groupby(record):
            return record.product_id, record.lot_id

        if not move_lines:
            return True

        grouped_quants = {}
        for k, g in groupby(self.quant_ids, key=_keys_groupby):
            grouped_quants[k] = sum(self.env['stock.quant'].concat(*g).mapped('quantity'))

        grouped_ops = {}
        for k, g in groupby(move_lines, key=_keys_groupby):
            grouped_ops[k] = sum(self.env['stock.move.line'].concat(*g).mapped('quantity'))

        return all(float_is_zero(grouped_quants.get(key, 0) - grouped_ops.get(key, 0), precision_digits=precision_digits) for key in grouped_quants) \
           and all(float_is_zero(grouped_ops.get(key, 0) - grouped_quants.get(key, 0), precision_digits=precision_digits) for key in grouped_ops)

    def _get_weight(self, picking_id=False):
        res = {}
        if picking_id:
            package_weights = defaultdict(float)
            res_groups = self.env['stock.move.line']._read_group(
                [('result_package_id', 'in', self.ids), ('product_id', '!=', False), ('picking_id', '=', picking_id)],
                ['result_package_id', 'product_id', 'product_uom_id', 'quantity'],
                ['__count'],
            )
            for result_package, product, product_uom, quantity, count in res_groups:
                package_weights[result_package.id] += (
                    count
                    * product_uom._compute_quantity(quantity, product.uom_id)
                    * product.weight
                )
        for package in self:
            weight = package.package_type_id.base_weight or 0.0
            if picking_id:
                res[package] = weight + package_weights[package.id]
            else:
                for quant in package.quant_ids:
                    weight += quant.quantity * quant.product_id.weight
                res[package] = weight
        return res
