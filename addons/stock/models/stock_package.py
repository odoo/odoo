# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from collections.abc import Iterable
import json
from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import format_list, groupby
from odoo.tools.barcode import check_barcode_encoding
from odoo.tools.float_utils import float_is_zero


class StockPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.package'
    _description = "Package"
    _order = 'name, id'
    _parent_name = 'parent_package_id'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char('Package Reference', copy=False, index='trigram', required=True)
    complete_name = fields.Char("Full Package Name", compute='_compute_complete_name', recursive=True, store=True)
    dest_complete_name = fields.Char("Package Name At Destination", compute='_compute_dest_complete_name', recursive=True)
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    contained_quant_ids = fields.One2many('stock.quant', compute="_compute_contained_quant_ids", search="_search_contained_quant_ids")
    content_description = fields.Char('Contents', compute="_compute_content_description")
    package_type_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=False, store=True, recursive=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination location', compute='_compute_location_dest_id', search="_search_location_dest_id")
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True, recursive=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_owner_id', search='_search_owner',
        readonly=True, compute_sudo=True)
    parent_package_id = fields.Many2one('stock.package', 'Container', index='btree_not_null')
    child_package_ids = fields.One2many('stock.package', 'parent_package_id', string='Contained Packages')
    all_children_package_ids = fields.One2many('stock.package', compute='_compute_all_children_package_ids', search="_search_all_children_package_ids")
    package_dest_id = fields.Many2one('stock.package', 'Destination Container', index='btree_not_null')
    outermost_package_id = fields.Many2one('stock.package', 'Outermost Destination Container', compute="_compute_outermost_package_id", search="_search_outermost_package_id", recursive=True)
    child_package_dest_ids = fields.One2many('stock.package', 'package_dest_id', 'Assigned Contained Packages')
    move_line_ids = fields.One2many('stock.move.line', compute="_compute_move_line_ids", search="_search_move_line_ids")
    picking_ids = fields.Many2many('stock.picking', string='Transfers', compute='_compute_picking_ids', search="_search_picking_ids", help="Transfers in which the Package is set as Destination Package")
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
    @api.depends_context('formatted_display_name', 'show_dest_package', 'show_src_package', 'is_done')
    def _compute_display_name(self):
        show_dest_package = self.env.context.get('show_dest_package')
        show_src_package = self.env.context.get('show_src_package')
        is_done = self.env.context.get('is_done')
        for package in self:
            if is_done:
                display_name = package.name
            elif show_dest_package:
                display_name = package.dest_complete_name
            elif show_src_package:
                display_name = package.complete_name
            else:
                display_name = package.name

            if package.env.context.get('formatted_display_name') and package.package_type_id and package.package_type_id.packaging_length and package.package_type_id.width and package.package_type_id.height:
                package.display_name = f"{display_name}\t--{package.package_type_id.packaging_length} x {package.package_type_id.width} x {package.package_type_id.height}--"
            else:
                package.display_name = display_name

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

    @api.depends('contained_quant_ids')
    def _compute_content_description(self):
        def format_content(qty, uom_name, product_name, display_uom):
            quantity = str(int(qty) if qty == int(qty) else qty)
            return " ".join([quantity, uom_name, product_name] if display_uom else [quantity, product_name])

        display_uom = self.env.user.has_group('uom.group_uom')
        for package in self:
            package_content = package.contained_quant_ids.grouped(lambda q: (q.product_uom_id, q.product_id))
            package_content = [(uom.name, product.display_name, sum(quants.mapped('quantity'))) for ((uom, product), quants) in package_content.items()]
            package.content_description = format_list(self.env, [format_content(qty, uom_name, product_name, display_uom) for (uom_name, product_name, qty) in package_content])

    def _compute_json_popover(self):
        for package in self:
            if not package._has_issues():
                package.json_popover = False
                continue
            location_names = package.move_line_ids.location_dest_id.mapped('display_name')
            package.json_popover = json.dumps({
                'title': self.env._("Multiple destinations"),
                'msg': self.env._("This package is currently set to be sent in %(location_names_list)s.", location_names_list=location_names),
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

    @api.depends('child_package_ids', 'child_package_ids.location_id', 'quant_ids')
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.quant_ids.filtered(lambda q: q.product_uom_id.compare(q.quantity, 0) > 0)
            if quants:
                package.location_id = quants[0].location_id
                if all(q.company_id == quants[0].company_id for q in package.quant_ids):
                    package.company_id = quants[0].company_id
            elif package.child_package_ids:
                package.location_id = package.child_package_ids[0].location_id
                if all(p.company_id == package.child_package_ids[0].company_id for p in package.child_package_ids):
                    package.company_id = package.child_package_ids[0].company_id

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

    @api.depends('package_dest_id', 'package_dest_id.outermost_package_id')
    def _compute_outermost_package_id(self):
        for package in self:
            if package.package_dest_id:
                package.outermost_package_id = package.package_dest_id.outermost_package_id
            else:
                package.outermost_package_id = package

    @api.depends('name')
    def _compute_valid_sscc(self):
        self.valid_sscc = False
        for package in self:
            if package.name:
                package.valid_sscc = check_barcode_encoding(package.name, 'sscc')

    def _search_all_children_package_ids(self, operator, value):
        packages = self.search_fetch(domain=[('id', operator, value)], field_names=['id'])
        return [('id', 'parent_of', packages.ids)]

    def _search_contained_quant_ids(self, operator, value):
        packages = self.search([('quant_ids', operator, value)])
        if packages:
            return [('id', 'parent_of', packages.ids)]
        else:
            return [('id', '=', False)]

    def _search_location_dest_id(self, operator, value):
        if operator not in ['in', 'not in']:
            return NotImplemented

        move_lines = self.env['stock.move.line'].search_fetch(
            domain=[('state', 'not in', ['done', 'cancel']), ('location_dest_id', operator, value)],
            field_names=['result_package_id'])
        all_package_ids = move_lines.result_package_id._get_all_package_dest_ids()

        return [('id', 'in', all_package_ids)]

    def _search_move_line_ids(self, operator, value):
        if operator not in ('in', 'any'):
            return NotImplemented
        if operator == 'any':
            operator = 'in'
            if isinstance(value, Domain):
                value = self.env['stock.move.line']._search(value)

        domain = Domain('state', 'not in', ['done', 'cancel'])
        pack_operator = 'in'
        if isinstance(value, Iterable) and tuple(value) == (False,):
            # Search for ('move_line_ids', '=', False), which means not assigned to any ongoing picking
            pack_operator = 'not in'
        else:
            domain &= Domain('id', operator, value)
        move_lines = self.env['stock.move.line'].search_fetch(domain=domain, field_names=['result_package_id'])
        all_package_ids = move_lines.result_package_id._get_all_package_dest_ids()

        return [('id', pack_operator, all_package_ids)]

    def _search_outermost_package_id(self, operator, value):
        if operator not in ['in', 'not in']:
            return NotImplemented

        packages = self.env['stock.package'].search_fetch(
            domain=[('package_dest_id', operator, value)],
            field_names=['child_package_dest_ids']
        )
        __, all_children_ids = packages._get_all_children_package_dest_ids()
        return [('id', 'in', all_children_ids)]

    def _search_owner(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return Domain('quant_ids.owner_id', operator, value)

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
                del vals['complete_name']
            if not vals.get('name'):
                package_type = self.env['stock.package.type'].browse(vals.get('package_type_id'))
                vals['name'] = package_type._get_next_name_by_sequence()

        return super().create(vals_list)

    def write(self, vals):
        if 'name' in vals and not vals.get('name'):
            # Recomputes the name according the sequence if the name was emptied.
            package_type = self.env['stock.package.type'].browse(vals.get('package_type_id'))
            for package in self:
                package_type = self.env['stock.package.type'].browse(vals.get('package_type_id', self.package_type_id.id))
                package.name = package_type._get_next_name_by_sequence()
            del vals['name']
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
        if vals.get('package_dest_id'):
            # Need to make sure we avoid a recursion within the package dests. Can't rely on the `parent_path` for destination packages.
            current_children_dest_ids = self._get_all_children_package_dest_ids()[1]
            if vals['package_dest_id'] in current_children_dest_ids:
                raise ValidationError(self.env._("A package can't have one of its contained packages as destination container."))

        return super().write(vals)

    def unpack(self):
        """ Unpacks quants directly inside the container, and remove contained packages from this package.
        """
        self.child_package_ids.parent_package_id = False
        if self.quant_ids:
            quants = self.quant_ids
            self.quant_ids.move_quants(message=self.env._("Quantities unpacked"), unpack=True)
            # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
            # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
            quants._quant_tasks()

    def action_add_to_picking(self):
        picking = self.env['stock.picking'].browse(self.env.context.get('picking_id'))
        if picking and self:
            picking.action_add_entire_packs(self.ids)

    def _pre_put_in_pack_hook(self, package_id=False, package_type_id=False, package_name=False, from_package_wizard=False):
        if self.move_line_ids._should_display_put_in_pack_wizard(package_id, package_type_id, package_name, from_package_wizard):
            action = self.env["ir.actions.actions"]._for_xml_id("stock.action_put_in_pack_wizard")
            action['context'] = {
                **literal_eval(action.get('context', '{}')),
                'default_package_ids': self.ids,
                'default_location_dest_id': self.location_dest_id[:1].id,
            }
            return action
        return False

    def _post_put_in_pack_hook(self):
        self.ensure_one()
        return self

    def action_put_in_pack(self, *, package_id=False, package_type_id=False, package_name=False):
        action = self._pre_put_in_pack_hook(package_id, package_type_id, package_name, self.env.context.get('from_package_wizard'))
        if action:
            return action

        if package_id:
            package = self.env['stock.package'].browse(package_id)
        else:
            package = self.env['stock.package'].create({
                'package_type_id': package_type_id,
                'name': package_name,
            })
        previous_dest_packages = self.env['stock.package'].browse(self._get_all_package_dest_ids())
        self.package_dest_id = package
        if packs_to_clear := previous_dest_packages.filtered(lambda p: not p.move_line_ids):
            # If following the put in pack, we broke the existing chain somehow, we need to free all now irrelevant packages
            packs_to_clear.package_dest_id = False

        # Since the uppermost package changed, there might be some new putaway to apply.
        package.move_line_ids._apply_putaway_strategy()
        return package._post_put_in_pack_hook()

    def action_remove_package(self):
        """ Removes all packages in self from the destination container tree.
            For move lines directly linked to a package (through result_package_id)
            - If the entire package is moved, remove the move lines entirely from the picking
            - Otherwise, just unset the packages as destination package
        """
        all_package_dest_ids = self._get_all_package_dest_ids()
        all_move_line_ids = set(self.move_line_ids.ids)
        move_line_ids_to_unlink = set()
        related_move_ids = set()
        move_line_ids_to_update = set()
        for line in self.move_line_ids:
            picking_ids = self.env.context.get('picking_ids')
            if picking_ids and line.picking_id.id not in picking_ids:
                continue
            if line.result_package_id.id in self.ids:
                if line.is_entire_pack:
                    move_line_ids_to_unlink.add(line.id)
                    related_move_ids.add(line.move_id.id)
                else:
                    move_line_ids_to_update.add(line.id)

        self.env['stock.move.line'].browse(move_line_ids_to_unlink).unlink()
        self.env['stock.move.line'].browse(move_line_ids_to_update).write({'result_package_id': False})
        # Unlink moves that had no initial demand and don't have any more associated move lines
        self.env['stock.move'].search_fetch([('id', 'in', related_move_ids), ('product_uom_qty', '=', 0), ('move_line_ids', '=', False)], field_names=['id']).unlink()

        # If packages in self are dest containers of other packages, remove them as their dest as well
        self.child_package_dest_ids.package_dest_id = False
        self.package_dest_id = False

        # If parent packages are now isolated from bottom-level packages, clear their destination container as well
        self.env['stock.package'].search_fetch([('id', 'in', all_package_dest_ids), ('move_line_ids', '=', False)], field_names=['id']).write({'package_dest_id': False})

        # If outermost packages were changed, different putaway rules may apply.
        self.env['stock.move.line'].browse(all_move_line_ids - move_line_ids_to_unlink)._apply_putaway_strategy()
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
        for k, g in groupby(self.contained_quant_ids, key=_keys_groupby):
            grouped_quants[k] = sum(self.env['stock.quant'].concat(*g).mapped('quantity'))

        grouped_ops = {}
        for k, g in groupby(move_lines, key=_keys_groupby):
            grouped_ops[k] = sum(self.env['stock.move.line'].concat(*g).mapped('quantity_product_uom'))

        return all(float_is_zero(grouped_quants.get(key, 0) - grouped_ops.get(key, 0), precision_digits=precision_digits) for key in grouped_quants) \
           and all(float_is_zero(grouped_ops.get(key, 0) - grouped_quants.get(key, 0), precision_digits=precision_digits) for key in grouped_ops)

    def _get_weight(self, picking_id=False):
        res = {}
        if picking_id:
            package_weights = defaultdict(float)
            # If we check the weight of an ongoing package, we may need to check its current child dest as well to known their own weight.
            children_by_dest_pack, all_pack_ids = self._get_all_children_package_dest_ids()
            base_weight_per_package_group = self.env['stock.package']._read_group(
                domain=[('id', 'in', all_pack_ids)],
                groupby=['id', 'package_type_id.base_weight']
            )
            base_weight_per_package = {pack.id: weight for pack, weight in base_weight_per_package_group}

            res_groups = self.env['stock.move.line']._read_group(
                [('result_package_id', 'in', all_pack_ids), ('product_id', '!=', False), ('picking_id', '=', picking_id)],
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
                for child_id in children_by_dest_pack.get(package, []):
                    res[package] += base_weight_per_package.get(child_id, 0) + package_weights.get(child_id, 0)
            else:
                # Take the base_weight of every contained package, so we include package only containing packages
                weight += sum(package.all_children_package_ids.mapped(lambda p: p.package_type_id.base_weight))
                for quant in package.contained_quant_ids:
                    weight += quant.quantity * quant.product_id.weight
                res[package] = weight
        return res

    def _has_issues(self):
        self.ensure_one()
        return len(self.move_line_ids.location_dest_id) > 1

    def _apply_dest_to_package(self, processed_package_ids=None):
        """ Moves the packages to their new container and checks that no contained quants of the new container
            would be in different locations.
        """
        packages_todo = self
        if processed_package_ids:
            packages_todo = packages_todo.filtered(lambda p: p.id not in processed_package_ids)
        else:
            processed_package_ids = set()
        packs_by_container = packages_todo.grouped('package_dest_id')
        for container_package, packages in packs_by_container.items():
            if not container_package:
                # If package has no future container package, needs to be removed from its current one.
                packages.write({'parent_package_id': False})
                processed_package_ids.update(packages.ids)
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
            processed_package_ids.update(packages.ids)
        # First level has been applied, need to check if next level needs to be applied as well.
        if packages_todo.parent_package_id.package_dest_id or packages_todo.parent_package_id.parent_package_id:
            packages_todo.parent_package_id._apply_dest_to_package(processed_package_ids)

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

    def _apply_package_dest_for_entire_packs(self, allowed_package_ids=None):
        """ When a package is assigned to a picking, if all of its container is added,
            then we consider the container to be added itself, unless the container
            is a reusable package itself.
        """
        for container, packages in self.grouped('parent_package_id').items():
            if container.child_package_ids == packages and container.package_type_id.package_use != 'reusable':
                if allowed_package_ids and container.id not in allowed_package_ids:
                    continue
                packages.package_dest_id = container
        if self.package_dest_id:
            # If one level was added, need to check if the upper container is fully contained as well.
            self.package_dest_id._apply_package_dest_for_entire_packs(allowed_package_ids)
