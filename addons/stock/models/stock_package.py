# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools import check_barcode_encoding, groupby
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.package'
    _description = "Packages"
    _order = 'name'
    _parent_name = 'parent_package_id'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(
        'Package Reference', copy=False, index='trigram', required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.package') or self.env._('Unknown Pack'))
    complete_name = fields.Char("Full Package Name", compute='_compute_complete_name', recursive=True, store=True)
    is_named_by_seq = fields.Boolean("Named by Sequence", compute="_compute_is_named_by_seq")
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    contained_quant_ids = fields.One2many('stock.quant', compute="_compute_contained_quant_ids", search="_search_contained_quant_ids")
    package_type_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=False, store=True)
    location_dest_ids = fields.Many2many('stock.location', 'Destination locations', compute='_compute_location_dest_ids')
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_owner_id', search='_search_owner',
        readonly=True, compute_sudo=True)
    parent_package_id = fields.Many2one('stock.package', 'Container Package')
    child_package_ids = fields.One2many('stock.package', 'parent_package_id', string='Contained Packages')
    package_dest_id = fields.Many2one('stock.package', 'Destination Container')
    move_line_ids = fields.One2many('stock.move.line', 'result_package_id', string='Move lines', readonly=True, copy=False)
    picking_ids = fields.Many2many('stock.picking', string='Transfers', compute='_compute_picking_ids', search="_search_picking_ids")
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")
    valid_sscc = fields.Boolean('Package name is valid SSCC', compute='_compute_valid_sscc')
    pack_date = fields.Date('Pack Date', default=fields.Date.today)
    parent_path = fields.Char(index=True)

    @api.depends('name', 'parent_package_id.complete_name')
    def _compute_complete_name(self):
        for package in self:
            if package.parent_package_id:
                package.complete_name = '%s > %s' % (package.parent_package_id.complete_name, package.name)
            else:
                package.complete_name = package.name

    @api.depends('quant_ids', 'child_package_ids')
    def _compute_contained_quant_ids(self):
        def fetch_all_children_quants(package_id, children_dict, quants_dict):
            quant_ids = quants_dict.get(package_id, [])
            if package_id not in children_dict:
                return quant_ids
            for child_pack_id in children_dict[package_id]:
                quant_ids += [*fetch_all_children_quants(child_pack_id, children_dict, quants_dict)]
            return quant_ids

        quants_by_pack = self.env['stock.quant']._read_group([('package_id', 'child_of', self.ids)], ['package_id'], ['id:array_agg'])
        children_by_pack = self.env['stock.package']._read_group([('id', 'child_of', self.ids)], ['parent_package_id'], ['id:array_agg'])
        quant_ids_by_pack_id = {package.id: quant_ids for package, quant_ids in quants_by_pack}
        child_ids_by_pack_id = {package.id: child_ids for package, child_ids in children_by_pack}

        for package in self:
            package.contained_quant_ids = [Command.set(fetch_all_children_quants(package.id, child_ids_by_pack_id, quant_ids_by_pack_id))]

    @api.depends('package_type_id', 'package_type_id.identification_method')
    def _compute_is_named_by_seq(self):
        for package in self:
            package.is_named_by_seq = package.package_type_id.identification_method == 'auto'

    def _compute_location_dest_ids(self):
        groups = self.env['stock.move.line']._read_group(
            domain=[('state', 'in', ['partially_available', 'assigned']), ('result_package_id', 'in', self.ids)],
            groupby=['result_package_id'], aggregates=['location_dest_id:array_agg'])
        dest_loc_by_packages = dict(groups)
        for package in self:
            package.location_dest_ids = [Command.set(dest_loc_by_packages.get(package, []))]

    @api.depends('contained_quant_ids.location_id', 'contained_quant_ids.company_id')
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.contained_quant_ids.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=q.product_uom_id.rounding) > 0)
            if quants:
                package.location_id = quants[0].location_id
                if all(q.company_id == quants[0].company_id for q in package.contained_quant_ids):
                    package.company_id = quants[0].company_id

    @api.depends('move_line_ids.picking_id')
    def _compute_picking_ids(self):
        for package in self:
            package.picking_ids = package.move_line_ids.picking_id

    def _search_picking_ids(self, operator, value):
        return [('move_line_ids.picking_id', operator, value)]

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

    @api.onchange('package_type_id')
    def _onchange_package_type(self):
        if self.package_type_id and self.package_type_id.identification_method == 'auto':
            self.name = '/'

    def _search_contained_quant_ids(self, operator, value):
        packages = self.search([('quant_ids', operator, value)])
        if packages:
            return [('id', 'parent_of', packages.ids)]
        else:
            return [('id', '=', False)]

    def _search_owner(self, operator, value):
        if value:
            packs = self.search([('quant_ids.owner_id', operator, value)])
        else:
            packs = self.search([('quant_ids', operator, value)])
        if packs:
            return [('id', 'in', packs.ids)]
        else:
            return [('id', '=', False)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            package_type = self.env['stock.package.type'].browse(vals.get('package_type_id'))
            if package_type.identification_method == 'auto':
                vals['name'] = package_type.sequence_id.next_by_id()

        return super().create(vals_list)

    def write(self, vals):
        if 'location_id' in vals:
            is_pack_empty = any(not pack.contained_quant_ids for pack in self)
            if not vals['location_id'] and not is_pack_empty:
                raise UserError(self.env._('Cannot remove the location of a non empty package'))
            elif vals['location_id']:
                if is_pack_empty and not self.env.context.get('move_parent_pack'):
                    raise UserError(self.env._('Cannot move an empty package'))
                # create a move from the old location to new location
                location_dest_id = self.env['stock.location'].browse(vals['location_id'])
                quant_to_move = self.contained_quant_ids.filtered(lambda q: q.quantity > 0)
                quant_to_move.move_quants(location_dest_id, message=self.env._('Package manually relocated'))
        return super().write(vals)

    def unpack(self):
        self.quant_ids.move_quants(message=self.env._("Quantities unpacked"), unpack=True)
        # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
        # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
        self.quant_ids._quant_tasks()

    def action_open_put_in_pack_wizard(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_put_in_pack_wizard")
        action['context'] = {
            'default_package_ids': self.ids,
        }
        return action

    def action_put_in_pack(self, package_type_id=False):
        package_vals = {}
        if package_type_id:
            package_vals['package_type_id'] = package_type_id

        new_package = self.env['stock.package'].create(package_vals)
        self.package_dest_id = new_package
        return True

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

    # TODO QUWO: To remove if we keep the `picking_ids` on the package directly
    # def _get_with_complete_parents(self, added_package_ids=None):
    #     if not added_package_ids:
    #         added_package_ids = set()
    #     pack_ids = set(self.ids)
    #     for parent_package in self.parent_package_id:
    #         if parent_package.id not in added_package_ids and set(parent_package.child_package_ids.ids).issubset(pack_ids):
    #             # All Packages contained in the parent are within self, so we can fetch that Package as well.
    #             added_package_ids.add(parent_package.id)

    #     if added_package_ids.issubset(pack_ids):
    #         # No parent was added, thus self already contains all relevant packages.
    #         return self

    #     # If we added at least one parent, we need to re-check with their own parents to see if we can have a further level.
    #     all_packages = self.env['stock.package'].browse(pack_ids | added_package_ids)
    #     return all_packages._get_with_complete_parents(added_package_ids)

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

    def _apply_dest_to_package(self):
        """ Moves the packages to their new container and checks that no contained quants of the new container
            would be in different locations.
        """
        packs_by_container = self.grouped('package_dest_id')
        for container_package, packages in packs_by_container.items():
            new_location = packages.location_id
            if len(new_location) > 1:
                raise UserError(self.env._("Packages %(duplicate_names)s are moved to different locations while being in the same container %(container_name)s.",
                                            duplicate_names=packages.mapped('name'), container_name=container_package.name))
            contained_quants = container_package.contained_quant_ids.filtered(lambda q: not float_is_zero(q.quantity, precision_rounding=q.product_uom_id.rounding))
            if contained_quants and contained_quants.location_id != new_location:
                raise UserError(self.env._("Can't move a container having packages in another location (%(old_location)s) to a different location (%(new_location)s).",
                                                old_location=contained_quants.location_id.name, new_location=new_location.name))
            packages.write({
                'parent_package_id': container_package.id,
                'package_dest_id': False,
            })
