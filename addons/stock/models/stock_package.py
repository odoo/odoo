# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json
from ast import literal_eval

from odoo import _, api, Command, fields, models
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.tools import format_list, groupby
from odoo.tools.barcode import check_barcode_encoding
from odoo.tools.float_utils import float_is_zero


class StockPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.package'
    _description = "Package"
    _order = 'name'
    _parent_name = 'parent_package_id'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(
        'Package Reference', copy=False, index='trigram', required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.package') or _('Unknown Pack'))
    complete_name = fields.Char("Full Package Name", compute='_compute_complete_name', recursive=True, store=True)
    dest_complete_name = fields.Char("Package Name At Destination", compute='_compute_dest_complete_name', recursive=True)
    is_named_by_seq = fields.Boolean("Named by Sequence", compute="_compute_is_named_by_seq")
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    contained_quant_ids = fields.One2many('stock.quant', compute="_compute_contained_quant_ids", search="_search_contained_quant_ids")
    package_type_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=False, store=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination location', compute='_compute_location_dest_id')
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_owner_id', search='_search_owner',
        readonly=True, compute_sudo=True)
    parent_package_id = fields.Many2one('stock.package', 'Container Package')
    child_package_ids = fields.One2many('stock.package', 'parent_package_id', string='Contained Packages')
    all_children_package_ids = fields.One2many('stock.package', compute='_compute_all_children_package_ids', search="_search_all_children_package_ids")
    package_dest_id = fields.Many2one('stock.package', 'Destination Container')
    final_package_dest_id = fields.Many2one('stock.package', 'Uppermost Destination Container', compute="_compute_final_package_dest_id")
    child_package_dest_ids = fields.One2many('stock.package', 'package_dest_id', 'Assigned Contained Packages')
    move_line_ids = fields.One2many('stock.move.line', compute="_compute_move_line_ids", search="_search_move_line_ids")
    picking_ids = fields.Many2many('stock.picking', string='Transfers', compute='_compute_picking_ids', search="_search_picking_ids")
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")
    valid_sscc = fields.Boolean('Package name is valid SSCC', compute='_compute_valid_sscc')
    pack_date = fields.Date('Pack Date', default=fields.Date.today)
    parent_path = fields.Char(index=True)
    json_popover = fields.Char('JSON data for popover widget', compute='_compute_json_popover')

    @api.depends('child_package_ids', 'child_package_ids.parent_path')
    def _compute_all_children_package_ids(self):
        def fetch_all_children(parent_id, children_by_pack):
            children_ids = children_by_pack.get(parent_id, [])
            sub_children_ids = [cid for child_id in children_ids for cid in fetch_all_children(child_id, children_by_pack)]
            return children_ids + sub_children_ids

        groups = self.env['stock.package']._read_group([('id', 'child_of', self.ids)], ['parent_package_id'], ['id:array_agg'])
        children_by_pack = {package.id: children_ids for package, children_ids in groups}
        for package in self:
            package.all_children_package_ids = [Command.set(fetch_all_children(package.id, children_by_pack))]

    @api.depends('complete_name', 'package_type_id.packaging_length', 'package_type_id.width', 'package_type_id.height')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        packages_to_process_ids = []
        for package in self:
            if package.env.context.get('formatted_display_name') and package.package_type_id and package.package_type_id.packaging_length and package.package_type_id.width and package.package_type_id.height:
                package.display_name = f"{package.complete_name}\t--{package.package_type_id.packaging_length} x {package.package_type_id.width} x {package.package_type_id.height}--"
            else:
                packages_to_process_ids.append(package.id)
        if packages_to_process_ids:
            super(StockPackage, self.env['stock.package'].browse(packages_to_process_ids))._compute_display_name()

    @api.depends('name', 'parent_package_id.complete_name')
    def _compute_complete_name(self):
        for package in self:
            if package.parent_package_id:
                package.complete_name = '%s > %s' % (package.parent_package_id.complete_name, package.name)
            else:
                package.complete_name = package.name

    @api.depends('name', 'package_dest_id.dest_complete_name')
    def _compute_dest_complete_name(self):
        for package in self:
            if package.package_dest_id:
                package.dest_complete_name = '%s > %s' % (package.package_dest_id.dest_complete_name, package.name)
            else:
                package.dest_complete_name = package.name

    @api.depends('quant_ids', 'all_children_package_ids.quant_ids')
    def _compute_contained_quant_ids(self):
        for package in self:
            package.contained_quant_ids = package.quant_ids | package.all_children_package_ids.quant_ids

    @api.depends('package_type_id', 'package_type_id.identification_method')
    def _compute_is_named_by_seq(self):
        for package in self:
            package.is_named_by_seq = package.package_type_id.identification_method == 'auto'

    def _compute_json_popover(self):
        for package in self:
            if not package._has_issues():
                package.json_popover = False
                continue
            location_names = format_list(self.env, package.move_line_ids.location_dest_id.mapped('display_name'))
            package.json_popover = json.dumps({
                'title': self.env._("Multiple destinations"),
                'msg': self.env._("This package is currently set to be sent in %(locations)s.", locations=location_names),
                'color': 'text-warning',
                'icon': 'fa-exclamation-triangle',
            })

    @api.depends('move_line_ids')
    def _compute_location_dest_id(self):
        for package in self:
            package.location_dest_id = package.move_line_ids.location_dest_id[:1] or False

    @api.depends('location_id', 'child_package_dest_ids')
    def _compute_move_line_ids(self):
        # location_id in depends to force the recompute of the move_line_ids if the package moves to another location.
        children_by_dest_pack, all_pack_ids = self._get_all_children_package_dest_ids()
        groups = self.env['stock.move.line']._read_group(
            domain=[('state', 'not in', ['done', 'cancel']), ('result_package_id', 'in', all_pack_ids)],
            groupby=['result_package_id'], aggregates=['id:array_agg'])
        move_lines_by_package = {package.id: move_line_ids for package, move_line_ids in groups}

        for package in self:
            move_line_ids = {line_id for child_id in children_by_dest_pack[package] for line_id in move_lines_by_package.get(child_id, [])}
            move_line_ids.update(move_lines_by_package.get(package.id, []))
            package.move_line_ids = [Command.set(list(move_line_ids))]

    @api.depends('child_package_ids', 'child_package_ids.parent_path', 'contained_quant_ids.location_id', 'contained_quant_ids.company_id')
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.contained_quant_ids.filtered(lambda q: q.product_uom_id.compare(q.quantity, 0) > 0)
            if quants:
                package.location_id = quants[0].location_id
                if all(q.company_id == quants[0].company_id for q in package.contained_quant_ids):
                    package.company_id = quants[0].company_id

    @api.depends('child_package_dest_ids')
    def _compute_picking_ids(self):
        children_by_dest_pack, all_pack_ids = self._get_all_children_package_dest_ids()
        groups = self.env['stock.move.line']._read_group(
            domain=[('state', 'not in', ['done', 'cancel']), ('result_package_id', 'in', all_pack_ids)],
            groupby=['result_package_id'], aggregates=['picking_id:array_agg'])
        pickings_by_package = {package.id: picking_ids for package, picking_ids in groups}

        for package in self:
            picking_ids = {picking_id for child_id in children_by_dest_pack[package] for picking_id in pickings_by_package.get(child_id, [])}
            picking_ids.update(pickings_by_package.get(package.id, []))
            package.picking_ids = [Command.set(list(picking_ids))]

    @api.depends('quant_ids.owner_id')
    def _compute_owner_id(self):
        for package in self:
            package.owner_id = False
            if package.quant_ids and all(
                q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids
            ):
                package.owner_id = package.quant_ids[0].owner_id

    @api.depends()
    def _compute_final_package_dest_id(self):
        def fetch_final_package(package):
            if package.package_dest_id:
                return fetch_final_package(package.package_dest_id)
            return package

        for package in self:
            package.final_package_dest_id = fetch_final_package(package.package_dest_id)

    @api.depends('name')
    def _compute_valid_sscc(self):
        self.valid_sscc = False
        for package in self:
            if package.name:
                package.valid_sscc = check_barcode_encoding(package.name, 'sscc')

    @api.onchange('package_type_id')
    def _onchange_package_type(self):
        if self.package_type_id and self.package_type_id.identification_method == 'auto':
            self.name = False

    def _search_all_children_package_ids(self, operator, value):
        packages = self.search_fetch(domain=[('id', operator, value)], field_names=['id'])
        return [('id', 'parent_of', packages.ids)]

    def _search_contained_quant_ids(self, operator, value):
        packages = self.search([('quant_ids', operator, value)])
        if packages:
            return [('id', 'parent_of', packages.ids)]
        else:
            return [('id', '=', False)]

    def _search_move_line_ids(self, operator, value):
        if operator not in ['in', 'not in']:
            return NotImplemented

        move_lines = self.env['stock.move.line'].search_fetch(
            domain=[('state', 'not in', ['done', 'cancel']), ('id', operator, value)],
            field_names=['result_package_id'])
        all_package_ids = move_lines.result_package_id._get_all_package_dest_ids()

        return [('id', 'in', all_package_ids)]

    def _search_owner(self, operator, value):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return NotImplemented
        return [('quant_ids.owner_id', operator, value)]

    def _search_picking_ids(self, operator, value):
        if operator not in ['in', 'not in']:
            return NotImplemented

        move_lines = self.env['stock.move.line'].search_fetch(
            domain=[('state', 'not in', ['done', 'cancel']), ('picking_id', operator, value)],
            field_names=['result_package_id'])
        all_package_ids = move_lines.result_package_id._get_all_package_dest_ids()

        return [('id', 'in', all_package_ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('complete_name'):
                vals['name'] = vals['complete_name']
            if not vals.get('name') and vals.get('package_type_id'):
                package_type = self.env['stock.package.type'].browse(vals['package_type_id'])
                vals['name'] = package_type._get_next_name_by_sequence()
            if 'name' in vals and not vals['name']:
                # Avoids issue when directly assigning a falsy value and bypassing the default.
                del vals['name']

        return super().create(vals_list)

    def write(self, vals):
        if vals.get('package_type_id'):
            package_type = self.env['stock.package.type'].browse(vals.get('package_type_id'))
            if package_type.identification_method == 'auto':
                for package in self:
                    if package.package_type_id != package_type:
                        package.name = package_type._get_next_name_by_sequence()
        if 'location_id' in vals:
            is_pack_empty = any(not pack.contained_quant_ids for pack in self)
            if not vals['location_id'] and not is_pack_empty:
                raise UserError(self.env._('Cannot remove the location of a non empty package'))
            elif vals['location_id']:
                if is_pack_empty:
                    raise UserError(self.env._('Cannot move an empty package'))
                # create a move from the old location to new location
                location_dest_id = self.env['stock.location'].browse(vals['location_id'])
                quant_to_move = self.contained_quant_ids.filtered(lambda q: q.quantity > 0)
                quant_to_move.move_quants(location_dest_id, message=self.env._('Package manually relocated'), up_to_parent_packages=self)
        return super().write(vals)

    def unpack(self):
        self.quant_ids.move_quants(message=self.env._("Quantities unpacked"), unpack=True)
        # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
        # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
        self.quant_ids._quant_tasks()

    def action_open_put_in_pack_wizard(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_put_in_pack_wizard")
        action['context'] = {
            **literal_eval(action.get('context', '{}')),
            'default_package_ids': self.ids,
            'default_location_dest_id': self.location_dest_id[:1].id,
        }
        return action

    def action_put_in_pack(self, package_id=False, package_type_id=False, package_name=False):
        if package_id:
            package = self.env['stock.package'].browse(package_id)
        else:
            package = self.env['stock.package'].create({
                'package_type_id': package_type_id,
                'name': package_name,
            })
        self.package_dest_id = package
        return True

    def action_remove_package(self):
        move_line_ids_to_unlink = set()
        move_line_ids_to_update = set()
        for line in self.move_line_ids:
            picking_id = self.env.context.get('picking_id')
            if picking_id and line.picking_id.id != picking_id:
                continue
            if line.is_entire_pack:
                move_line_ids_to_unlink.add(line.id)
            else:
                move_line_ids_to_update.add(line.id)

        self.env['stock.move.line'].browse(move_line_ids_to_unlink).unlink()
        self.env['stock.move.line'].browse(move_line_ids_to_update).write({'result_package_id': False})

        # If packages in self are dest containers of other packages, remove them as their dest as well
        self.child_package_dest_ids.package_dest_id = False
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

    def _get_weight(self, picking_id=False):
        res = {}
        if picking_id:
            package_weights = defaultdict(float)
            res_groups = self.env['stock.move.line']._read_group(
                [('result_package_id', 'child_of', self.ids), ('product_id', '!=', False), ('picking_id', '=', picking_id)],
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
                for quant in package.contained_quant_ids:
                    weight += quant.quantity * quant.product_id.weight
                res[package] = weight
        return res

    def _has_issues(self):
        self.ensure_one()
        return len(self.move_line_ids.location_dest_id) > 1

    def _apply_dest_to_package(self):
        """ Moves the packages to their new container and checks that no contained quants of the new container
            would be in different locations.
        """
        packs_by_container = self.grouped('package_dest_id')
        for container_package, packages in packs_by_container.items():
            if not container_package:
                # If package has no future container package, needs to be removed from its current one.
                packages.write({'parent_package_id': False})
                continue
            # At this point, the packages were already moved so we need to check their current position.
            new_location = packages.location_id
            if len(new_location) > 1:
                raise UserError(self.env._("Packages %(duplicate_names)s are moved to different locations while being in the same container %(container_name)s.",
                                            duplicate_names=packages.mapped('name'), container_name=container_package.name))
            contained_quants = container_package.contained_quant_ids.filtered(lambda q: not float_is_zero(q.quantity, precision_rounding=q.product_uom_id.rounding))
            if contained_quants and contained_quants.location_id != new_location:
                old_location = contained_quants.location_id - new_location
                raise UserError(self.env._("Can't move a container having packages in another location (%(old_location)s) to a different location (%(new_location)s).",
                                            old_location=old_location.display_name, new_location=new_location.display_name))
            packages.write({
                'parent_package_id': container_package.id,
                'package_dest_id': False,
            })
        # First level has been applied, need to check if next level needs to be applied as well.
        if self.parent_package_id.package_dest_id:
            self.parent_package_id._apply_dest_to_package()

    def _get_all_children_package_dest_ids(self):
        """ Gets all child packages that have the packages in self as their `package_dest_id` recursively.
            Since we can only have a single _parent field on the model, we need to do this manually.
            :returns: A dict for each record in self containing all packages that have it as `package_dest_id`, even remotely
            :returns: A list containing all children ids, regardless of their parents
        """
        def fetch_next_children(packages):
            if packages.child_package_dest_ids:
                return set(packages.ids) | fetch_next_children(packages.child_package_dest_ids)
            else:
                return set(packages.ids)

        all_children_ids = set(self.ids)
        all_children_by_pack = defaultdict(list)
        for package in self:
            if package.child_package_dest_ids:
                child_ids = list(fetch_next_children(package.child_package_dest_ids))
                all_children_ids.update(child_ids)
                all_children_by_pack[package] = child_ids

        return all_children_by_pack, all_children_ids

    def _get_all_package_dest_ids(self):
        """ Gets all parent destination packages recursively.
            Since we can only have a single _parent field on the model, we need to do this manually.
            :returns: A list containing all parent ids
        """
        def fetch_next_parents(packages):
            if packages.package_dest_id:
                return set(packages.ids) | fetch_next_parents(packages.package_dest_id)
            else:
                return set(packages.ids)

        return list(fetch_next_parents(self))

    def _apply_package_dest_for_entire_packs(self):
        """ When a package is assigned to a picking, if all of its container is added,
            then we consider the container to be added itself.
        """
        for container, packages in self.grouped('parent_package_id').items():
            if container.child_package_ids == packages:
                packages.package_dest_id = container
        if self.package_dest_id:
            # If one level was added, need to check if the upper container is fully contained as well.
            self.package_dest_id._apply_package_dest_for_entire_packs()
