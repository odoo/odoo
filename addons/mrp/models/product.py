# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
from datetime import timedelta
import operator as py_operator
from odoo import api, fields, models, _
from odoo.exceptions import UserError


PY_OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne,
    'in': lambda elem, container: elem in container,
    'not in': lambda elem, container: elem not in container,
}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bom_line_ids = fields.One2many('mrp.bom.line', 'product_tmpl_id', 'BoM Components')
    bom_ids = fields.One2many('mrp.bom', 'product_tmpl_id', 'Bill of Materials')
    bom_count = fields.Integer('# Bill of Material',
        compute='_compute_bom_count', compute_sudo=False)
    used_in_bom_count = fields.Integer('# of BoM Where is Used',
        compute='_compute_used_in_bom_count', compute_sudo=False)
    mrp_product_qty = fields.Float('Manufactured', digits='Product Unit',
        compute='_compute_mrp_product_qty', compute_sudo=False)
    is_kits = fields.Boolean(compute='_compute_is_kits', search='_search_is_kits')

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count(
                ['|', ('product_tmpl_id', 'in', product.ids), ('byproduct_ids.product_id.product_tmpl_id', 'in', product.ids)]
            )

    @api.depends_context('company')
    def _compute_is_kits(self):
        domain = [('product_tmpl_id', 'in', self.ids), ('type', '=', 'phantom'), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
        bom_mapping = self.env['mrp.bom'].sudo().search_read(domain, ['product_tmpl_id'])
        kits_ids = set(b['product_tmpl_id'][0] for b in bom_mapping)
        for template in self:
            template.is_kits = (template.id in kits_ids)

    def _search_is_kits(self, operator, value):
        if operator != 'in':
            return NotImplemented
        bom_tmpl_query = self.env['mrp.bom'].sudo()._search(
            [('company_id', 'in', [False] + self.env.companies.ids),
             ('type', '=', 'phantom'), ('active', '=', True)])
        return [('id', 'in', bom_tmpl_query.subselect('product_tmpl_id'))]

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for template in self:
            if template.is_kits:
                template.show_on_hand_qty_status_button = template.product_variant_count <= 1
                template.show_forecasted_qty_status_button = False

    def _should_open_product_quants(self):
        return super()._should_open_product_quants() or self.is_kits

    def _compute_used_in_bom_count(self):
        for template in self:
            template.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_tmpl_id', 'in', template.ids)])

    def write(self, vals):
        if 'active' in vals:
            self.filtered(lambda p: p.active != vals['active']).with_context(active_test=False).bom_ids.write({
                'active': vals['active']
            })
        return super().write(vals)

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_form_action")
        action['domain'] = [('bom_line_ids.product_tmpl_id', '=', self.id)]
        return action

    def _compute_mrp_product_qty(self):
        for template in self:
            template.mrp_product_qty = template.uom_id.round(sum(template.mapped('product_variant_ids').mapped('mrp_product_qty')))

    def action_view_mos(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_action")
        action['domain'] = [('state', '=', 'done'), ('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'search_default_filter_plan_date': 1,
        }
        return action

    def action_archive(self):
        filtered_products = self.env['mrp.bom.line'].search([('product_id', 'in', self.product_variant_ids.ids), ('bom_id.active', '=', True)]).product_id.mapped('display_name')
        res = super().action_archive()
        if filtered_products:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                'title': _("Note that product(s): '%s' is/are still linked to active Bill of Materials, "
                            "which means that the product can still be used on it/them.", filtered_products),
                'type': 'warning',
                'sticky': True,  #True/False will display for few seconds if false
                'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        return res

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('mrp.menu_mrp_root').id]


class ProductProduct(models.Model):
    _inherit = "product.product"

    variant_bom_ids = fields.One2many('mrp.bom', 'product_id', 'BOM Product Variants')
    bom_line_ids = fields.One2many('mrp.bom.line', 'product_id', 'BoM Components')
    bom_count = fields.Integer('# Bill of Material',
        compute='_compute_bom_count', compute_sudo=False)
    used_in_bom_count = fields.Integer('# BoM Where Used',
        compute='_compute_used_in_bom_count', compute_sudo=False)
    mrp_product_qty = fields.Float('Manufactured', digits='Product Unit',
        compute='_compute_mrp_product_qty', compute_sudo=False)
    is_kits = fields.Boolean(compute="_compute_is_kits", search='_search_is_kits')

    # Catalog related fields
    product_catalog_product_is_in_bom = fields.Boolean(
        compute='_compute_product_is_in_bom_and_mo',
        search='_search_product_is_in_bom',
    )

    product_catalog_product_is_in_mo = fields.Boolean(
        compute='_compute_product_is_in_bom_and_mo',
        search='_search_product_is_in_mo',
    )

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count([
                '|', '|', ('byproduct_ids.product_id', 'in', product.ids), ('product_id', 'in', product.ids),
                '&', ('product_id', '=', False), ('product_tmpl_id', 'in', product.product_tmpl_id.ids),
            ])

    @api.depends_context('company')
    def _compute_is_kits(self):
        domain = ['&', '&', ('type', '=', 'phantom'),
                       '|', ('company_id', '=', False),
                            ('company_id', '=', self.env.company.id),
                       '|', ('product_id', 'in', self.ids),
                            '&', ('product_id', '=', False),
                                 ('product_tmpl_id', 'in', self.product_tmpl_id.ids)]
        bom_mapping = self.env['mrp.bom'].sudo().search_read(domain, ['product_tmpl_id', 'product_id'])
        kits_template_ids = set([])
        kits_product_ids = set([])
        for bom_data in bom_mapping:
            if bom_data['product_id']:
                kits_product_ids.add(bom_data['product_id'][0])
            else:
                kits_template_ids.add(bom_data['product_tmpl_id'][0])
        for product in self:
            product.is_kits = (product.id in kits_product_ids or product.product_tmpl_id.id in kits_template_ids)

    def _search_is_kits(self, operator, value):
        if operator != 'in':
            return NotImplemented
        bom_tmpl_query = self.env['mrp.bom'].sudo()._search(
            [('company_id', 'in', [False] + self.env.companies.ids),
             ('active', '=', True),
             ('type', '=', 'phantom'), ('product_id', '=', False)])
        bom_product_query = self.env['mrp.bom'].sudo()._search(
            [('company_id', 'in', [False] + self.env.companies.ids),
             ('type', '=', 'phantom'), ('product_id', '!=', False)])
        return [
            '|', ('product_tmpl_id', 'in', bom_tmpl_query.subselect('product_tmpl_id')),
            ('id', 'in', bom_product_query.subselect('product_id'))
        ]

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for product in self:
            if product.is_kits:
                product.show_on_hand_qty_status_button = True
                product.show_forecasted_qty_status_button = False

    def _compute_used_in_bom_count(self):
        for product in self:
            product.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_id', 'in', product.ids)])

    @api.depends_context('order_id')
    def _compute_product_is_in_bom_and_mo(self):
        # Just to enable the _search method
        self.product_catalog_product_is_in_bom = False
        self.product_catalog_product_is_in_mo = False

    def _search_product_is_in_bom(self, operator, value):
        if operator != 'in':
            return NotImplemented
        product_ids = self.env['mrp.bom.line'].search([
            ('bom_id', '=', self.env.context.get('order_id', '')),
        ]).product_id.ids
        return [('id', operator, product_ids)]

    def _search_product_is_in_mo(self, operator, value):
        if operator != 'in':
            return NotImplemented
        product_ids = self.env['mrp.production'].search([
            ('id', 'in', [self.env.context.get('order_id', '')]),
        ]).move_raw_ids.product_id.ids
        return [('id', operator, product_ids)]

    def write(self, vals):
        if 'active' in vals:
            self.filtered(lambda p: p.active != vals['active']).with_context(active_test=False).variant_bom_ids.write({
                'active': vals['active']
            })
        return super().write(vals)

    def get_components(self):
        """ Return the components list ids in case of kit product.
        Return the product itself otherwise"""
        self.ensure_one()
        bom_kit = self.env['mrp.bom']._bom_find(self, bom_type='phantom')[self]
        if bom_kit:
            boms, bom_sub_lines = bom_kit.explode(self, 1)
            return [bom_line.product_id.id for bom_line, data in bom_sub_lines if bom_line.product_id.is_storable]
        else:
            return super(ProductProduct, self).get_components()

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_form_action")
        action['domain'] = [('bom_line_ids.product_id', '=', self.id)]
        return action

    def _compute_mrp_product_qty(self):
        date_from = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=365))
        #TODO: state = done?
        domain = [('state', '=', 'done'), ('product_id', 'in', self.ids), ('date_start', '>', date_from)]
        read_group_res = self.env['mrp.production']._read_group(domain, ['product_id'], ['product_uom_qty:sum'])
        mapped_data = {product.id: qty for product, qty in read_group_res}
        for product in self:
            if not product.id:
                product.mrp_product_qty = 0.0
                continue
            product.mrp_product_qty = product.uom_id.round(mapped_data.get(product.id, 0))

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        """ When the product is a kit, this override computes the fields :
         - 'virtual_available'
         - 'qty_available'
         - 'incoming_qty'
         - 'outgoing_qty'
         - 'free_qty'

        This override is used to get the correct quantities of products
        with 'phantom' as BoM type.
        """
        bom_kits = self.env['mrp.bom']._bom_find(self, bom_type='phantom')
        kits = self.filtered(lambda p: bom_kits.get(p))
        regular_products = self - kits
        res = (
            super(ProductProduct, regular_products)._compute_quantities_dict(lot_id, owner_id, package_id, from_date=from_date, to_date=to_date)
            if regular_products
            else {}
        )
        qties = self.env.context.get("mrp_compute_quantities", {})
        qties.update(res)
        # pre-compute bom lines and identify missing kit components to prefetch
        bom_sub_lines_per_kit = {}
        prefetch_component_ids = set()
        for product in bom_kits:
            __, bom_sub_lines = bom_kits[product].explode(product, 1)
            bom_sub_lines_per_kit[product] = bom_sub_lines
            for bom_line, __ in bom_sub_lines:
                if bom_line.product_id.id not in qties:
                    prefetch_component_ids.add(bom_line.product_id.id)
        # compute kit quantities
        for product in bom_kits:
            bom_sub_lines = bom_sub_lines_per_kit[product]
            # group lines by component
            bom_sub_lines_grouped = collections.defaultdict(list)
            for info in bom_sub_lines:
                bom_sub_lines_grouped[info[0].product_id].append(info)
            ratios_virtual_available = []
            ratios_qty_available = []
            ratios_incoming_qty = []
            ratios_outgoing_qty = []
            ratios_free_qty = []

            for component, bom_sub_lines in bom_sub_lines_grouped.items():
                component = component.with_context(mrp_compute_quantities=qties).with_prefetch(prefetch_component_ids)
                qty_per_kit = 0
                for bom_line, bom_line_data in bom_sub_lines:
                    if not component.is_storable or bom_line.product_uom_id.is_zero(bom_line_data['qty']):
                        # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                        # to avoid a division by zero. The same logic is applied to non-storable products as those
                        # products have 0 qty available.
                        continue
                    uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                    qty_per_kit += bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, round=False, raise_if_failure=False)
                if not qty_per_kit:
                    continue
                component_res = (
                    qties.get(component.id)
                    if component.id in qties
                    else {
                        "virtual_available": component.uom_id.round(component.virtual_available),
                        "qty_available": component.uom_id.round(component.qty_available),
                        "incoming_qty": component.uom_id.round(component.incoming_qty),
                        "outgoing_qty": component.uom_id.round(component.outgoing_qty),
                        "free_qty": component.uom_id.round(component.free_qty),
                    }
                )
                ratios_virtual_available.append(component.uom_id.round(component_res["virtual_available"] / qty_per_kit, rounding_method='DOWN'))
                ratios_qty_available.append(component.uom_id.round(component_res["qty_available"] / qty_per_kit, rounding_method='DOWN'))
                ratios_incoming_qty.append(component.uom_id.round(component_res["incoming_qty"] / qty_per_kit, rounding_method='DOWN'))
                ratios_outgoing_qty.append(component.uom_id.round(component_res["outgoing_qty"] / qty_per_kit, rounding_method='DOWN'))
                ratios_free_qty.append(component.uom_id.round(component_res["free_qty"] / qty_per_kit, rounding_method='DOWN'))
            if bom_sub_lines and ratios_virtual_available:  # Guard against all cnsumable bom: at least one ratio should be present.
                res[product.id] = {
                    'virtual_available': component.uom_id.round(min(ratios_virtual_available) * bom_kits[product].product_qty) // 1,
                    'qty_available': component.uom_id.round(min(ratios_qty_available) * bom_kits[product].product_qty) // 1,
                    'incoming_qty': component.uom_id.round(min(ratios_incoming_qty) * bom_kits[product].product_qty) // 1,
                    'outgoing_qty': component.uom_id.round(min(ratios_outgoing_qty) * bom_kits[product].product_qty) // 1,
                    'free_qty': component.uom_id.round(min(ratios_free_qty) * bom_kits[product].product_qty) // 1,
                }
            else:
                res[product.id] = {
                    'virtual_available': 0,
                    'qty_available': 0,
                    'incoming_qty': 0,
                    'outgoing_qty': 0,
                    'free_qty': 0,
                }

        return res

    def action_view_bom(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.product_open_bom")
        template_ids = self.mapped('product_tmpl_id').ids
        # bom specific to this variant or global to template or that contains the product as a byproduct
        action['context'] = {
            'default_product_tmpl_id': template_ids[0],
            'default_product_id': self.env.user.has_group('product.group_product_variant') and self.ids[0] or False,
        }
        action['domain'] = ['|', '|', ('byproduct_ids.product_id', 'in', self.ids), ('product_id', 'in', self.ids), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', template_ids)]
        return action

    def action_view_mos(self):
        action = self.product_tmpl_id.action_view_mos()
        action['domain'] = [('state', '=', 'done'), ('product_id', 'in', self.ids)]
        return action

    def action_open_quants(self):
        bom_kits = self.env['mrp.bom']._bom_find(self, bom_type='phantom')
        components = self - self.env['product.product'].concat(*list(bom_kits.keys()))
        for product in bom_kits:
            boms, bom_sub_lines = bom_kits[product].explode(product, 1)
            components |= self.env['product.product'].concat(*[l[0].product_id for l in bom_sub_lines])
        res = super(ProductProduct, components).action_open_quants()
        if bom_kits:
            res['context'].pop('default_product_tmpl_id', None)
        return res

    def _match_all_variant_values(self, product_template_attribute_value_ids):
        """ It currently checks that all variant values (`product_template_attribute_value_ids`)
        are in the product (`self`).

        If multiple values are encoded for the same attribute line, only one of
        them has to be found on the variant.
        """
        self.ensure_one()
        # The intersection of the values of the product and those of the line satisfy:
        # * the number of items equals the number of attributes (since a product cannot
        #   have multiple values for the same attribute),
        # * the attributes are a subset of the attributes of the line.
        return len(self.product_template_attribute_value_ids & product_template_attribute_value_ids) == len(product_template_attribute_value_ids.attribute_id)

    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        or_domains.append([
            ('production_id', '=', False),
            ('location_id.usage', '=', 'production'),
            ('move_id.unbuild_id', '!=', False),
        ])
        return super()._count_returned_sn_products_domain(sn_lot, or_domains)

    def _search_qty_available_new(self, operator, value, lot_id=False, owner_id=False, package_id=False):
        '''extending the method in stock.product to take into account kits'''
        op = PY_OPERATORS.get(operator)
        if not op:
            return NotImplemented
        product_ids = super(ProductProduct, self)._search_qty_available_new(operator, value, lot_id, owner_id, package_id)
        kit_boms = self.env['mrp.bom'].search([('type', "=", 'phantom')])
        kit_products = self.env['product.product']
        for kit in kit_boms:
            if kit.product_id:
                kit_products |= kit.product_id
            else:
                kit_products |= kit.product_tmpl_id.product_variant_ids
        for product in kit_products:
            if op(product.qty_available, value):
                product_ids.append(product.id)
            elif product.id in product_ids:
                product_ids.pop(product_ids.index(product.id))
        return list(set(product_ids))

    def action_archive(self):
        filtered_products = self.env['mrp.bom.line'].search([('product_id', 'in', self.ids), ('bom_id.active', '=', True)]).product_id.mapped('display_name')
        res = super().action_archive()
        if filtered_products:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                'title': _("Note that product(s): '%s' is/are still linked to active Bill of Materials, "
                            "which means that the product can still be used on it/them.", filtered_products),
                'type': 'warning',
                'sticky': True,  #True/False will display for few seconds if false
                'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        return res

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('mrp.menu_mrp_root').id]

    def _update_uom(self, to_uom_id):
        for uom, product_template, boms in self.env['mrp.bom']._read_group(
            [('product_tmpl_id', 'in', self.product_tmpl_id.ids)],
            ['product_uom_id', 'product_tmpl_id'],
            ['id:recordset'],
        ):
            if product_template.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product_template.uom_id.name))
            boms.product_uom_id = to_uom_id

        for uom, product, bom_lines in self.env['mrp.bom.line']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if product.product_tmpl_id.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            bom_lines.product_uom_id = to_uom_id

        for uom, product, productions in self.env['mrp.production']._read_group(
            [('product_id', 'in', self.ids)],
            ['product_uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if product.product_tmpl_id.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            productions.product_uom_id = to_uom_id

        return super()._update_uom(to_uom_id)
