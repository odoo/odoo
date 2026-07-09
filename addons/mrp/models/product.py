# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


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

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count(
                ['|', ('product_tmpl_id', 'in', product.ids), ('byproduct_ids.product_id.product_tmpl_id', 'in', product.ids)]
            )

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()

    def _should_open_product_quants(self):
        return super()._should_open_product_quants()

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
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_line_action_used_in_boms")
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        action['context'] = {'search_default_bom_active': True}
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

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()

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

    def get_routes_actions(self):
        actions = super().get_routes_actions()
        if self.bom_ids:
            actions += ['manufacture']
        return actions

    def get_components(self):
        return super().get_components()

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_line_action_used_in_boms")
        action['domain'] = [('product_id', '=', self.id)]
        action['context'] = {'search_default_bom_active': True}
        return action

    def _compute_mrp_product_qty(self):
        date_from = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=365))
        domain = [
            ('production_id.state', '=', 'done'),
            ('product_id', 'in', self.ids),
            ('production_id.date_start', '>', date_from),
            ('state', '!=', 'cancel'),
            ('picked', '=', True),
        ]
        read_group_res = self.env['stock.move']._read_group(domain, ['product_id', 'uom_id'], ['quantity:sum'])
        mapped_data = collections.defaultdict(float)
        for product, uom, qty in read_group_res:
            if uom != product.uom_id:
                qty = uom._compute_quantity(qty, product.uom_id)
            mapped_data[product.id] += qty
        for product in self:
            if not product.id:
                product.mrp_product_qty = 0.0
                continue
            product.mrp_product_qty = product.uom_id.round(mapped_data.get(product.id, 0))

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
        return super().action_open_quants()

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
        return super()._search_qty_available_new(operator, value, lot_id, owner_id, package_id)

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
            ['uom_id', 'product_tmpl_id'],
            ['id:recordset'],
        ):
            if product_template.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product_template.uom_id.name))
            boms.uom_id = to_uom_id

        for uom, product, bom_lines in self.env['mrp.bom.line']._read_group(
            [('product_id', 'in', self.ids)],
            ['uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if product.product_tmpl_id.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            bom_lines.uom_id = to_uom_id

        for uom, product, productions in self.env['mrp.production']._read_group(
            [('product_id', 'in', self.ids)],
            ['uom_id', 'product_id'],
            ['id:recordset'],
        ):
            if product.product_tmpl_id.uom_id != uom:
                raise UserError(_('As other units of measure (ex : %(problem_uom)s) '
                'than %(uom)s have already been used for this product, the change of unit of measure can not be done.'
                'If you want to change it, please archive the product and create a new one.',
                problem_uom=uom.name, uom=product.product_tmpl_id.uom_id.name))
            productions.uom_id = to_uom_id

        return super()._update_uom(to_uom_id)
