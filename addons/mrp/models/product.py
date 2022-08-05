# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from itertools import groupby
import operator as py_operator
from odoo import api, fields, models
from odoo.tools import groupby
from odoo.tools.float_utils import float_round, float_is_zero


OPERATORS = {
    '<': py_operator.lt,
    '>': py_operator.gt,
    '<=': py_operator.le,
    '>=': py_operator.ge,
    '=': py_operator.eq,
    '!=': py_operator.ne
}

class ProductTemplate(models.Model):
    _inherit = "product.template"

    bom_line_ids = fields.One2many('mrp.bom.line', 'product_tmpl_id', 'BoM Components')
    bom_ids = fields.One2many('mrp.bom', 'product_tmpl_id', 'Bill of Materials')
    bom_count = fields.Integer('# Bill of Material',
        compute='_compute_bom_count', compute_sudo=False)
    used_in_bom_count = fields.Integer('# of BoM Where is Used',
        compute='_compute_used_in_bom_count', compute_sudo=False)
    mrp_product_qty = fields.Float('Manufactured', digits='Product Unit of Measure',
        compute='_compute_mrp_product_qty', compute_sudo=False)
    produce_delay = fields.Float(
        'Manufacturing Lead Time', default=0.0,
        help="Average lead time in days to manufacture this product. In the case of multi-level BOM, the manufacturing lead times of the components will be added. In case the product is subcontracted, this can be used to determine the date at which components should be sent to the subcontractor.")
    is_kits = fields.Boolean(compute='_compute_is_kits', compute_sudo=False)
    days_to_prepare_mo = fields.Float(
        string="Days to prepare Manufacturing Order", default=0.0,
        help="Create and confirm Manufacturing Orders these many days in advance, to have enough time to replenish components or manufacture semi-finished products.\n"
             "Note that this does not affect the MO scheduled date, which still respects the just-in-time mechanism.")

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count(['|', ('product_tmpl_id', '=', product.id), ('byproduct_ids.product_id.product_tmpl_id', '=', product.id)])

    def _compute_is_kits(self):
        domain = [('product_tmpl_id', 'in', self.ids), ('type', '=', 'phantom')]
        bom_mapping = self.env['mrp.bom'].search_read(domain, ['product_tmpl_id'])
        kits_ids = set(b['product_tmpl_id'][0] for b in bom_mapping)
        for template in self:
            template.is_kits = (template.id in kits_ids)

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for template in self:
            if template.is_kits:
                template.show_on_hand_qty_status_button = True
                template.show_forecasted_qty_status_button = False

    def _compute_used_in_bom_count(self):
        for template in self:
            template.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_tmpl_id', '=', template.id)])

    def write(self, values):
        if 'active' in values:
            self.filtered(lambda p: p.active != values['active']).with_context(active_test=False).bom_ids.write({
                'active': values['active']
            })
        return super().write(values)

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_form_action")
        action['domain'] = [('bom_line_ids.product_tmpl_id', '=', self.id)]
        return action

    def _compute_mrp_product_qty(self):
        for template in self:
            template.mrp_product_qty = float_round(sum(template.mapped('product_variant_ids').mapped('mrp_product_qty')), precision_rounding=template.uom_id.rounding)

    def action_view_mos(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_report")
        action['domain'] = [('state', '=', 'done'), ('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'graph_measure': 'product_uom_qty',
            'time_ranges': {'field': 'date_planned_start', 'range': 'last_365_days'}
        }
        return action

    def action_compute_bom_days(self):
        templates = self.filtered(lambda t: t.bom_count > 0)
        if templates:
            return templates.mapped('product_variant_id').action_compute_bom_days()

class ProductProduct(models.Model):
    _inherit = "product.product"

    variant_bom_ids = fields.One2many('mrp.bom', 'product_id', 'BOM Product Variants')
    bom_line_ids = fields.One2many('mrp.bom.line', 'product_id', 'BoM Components')
    bom_count = fields.Integer('# Bill of Material',
        compute='_compute_bom_count', compute_sudo=False)
    used_in_bom_count = fields.Integer('# BoM Where Used',
        compute='_compute_used_in_bom_count', compute_sudo=False)
    mrp_product_qty = fields.Float('Manufactured', digits='Product Unit of Measure',
        compute='_compute_mrp_product_qty', compute_sudo=False)
    is_kits = fields.Boolean(compute="_compute_is_kits", compute_sudo=False)

    def _compute_bom_count(self):
        for product in self:
            product.bom_count = self.env['mrp.bom'].search_count(['|', '|', ('byproduct_ids.product_id', '=', product.id), ('product_id', '=', product.id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product.product_tmpl_id.id)])

    def _compute_is_kits(self):
        domain = ['&', ('type', '=', 'phantom'),
                       '|', ('product_id', 'in', self.ids),
                            '&', ('product_id', '=', False),
                                 ('product_tmpl_id', 'in', self.product_tmpl_id.ids)]
        bom_mapping = self.env['mrp.bom'].search_read(domain, ['product_tmpl_id', 'product_id'])
        kits_template_ids = set([])
        kits_product_ids = set([])
        for bom_data in bom_mapping:
            if bom_data['product_id']:
                kits_product_ids.add(bom_data['product_id'][0])
            else:
                kits_template_ids.add(bom_data['product_tmpl_id'][0])
        for product in self:
            product.is_kits = (product.id in kits_product_ids or product.product_tmpl_id.id in kits_template_ids)

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for product in self:
            if product.is_kits:
                product.show_on_hand_qty_status_button = True
                product.show_forecasted_qty_status_button = False

    def _compute_used_in_bom_count(self):
        for product in self:
            product.used_in_bom_count = self.env['mrp.bom'].search_count([('bom_line_ids.product_id', '=', product.id)])

    def write(self, values):
        if 'active' in values:
            self.filtered(lambda p: p.active != values['active']).with_context(active_test=False).variant_bom_ids.write({
                'active': values['active']
            })
        return super().write(values)

    def get_components(self):
        """ Return the components list ids in case of kit product.
        Return the product itself otherwise"""
        self.ensure_one()
        bom_kit = self.env['mrp.bom']._bom_find(self, bom_type='phantom')[self]
        if bom_kit:
            boms, bom_sub_lines = bom_kit.explode(self, 1)
            return [bom_line.product_id.id for bom_line, data in bom_sub_lines if bom_line.product_id.type == 'product']
        else:
            return super(ProductProduct, self).get_components()

    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_bom_form_action")
        action['domain'] = [('bom_line_ids.product_id', '=', self.id)]
        return action

    def _compute_mrp_product_qty(self):
        date_from = fields.Datetime.to_string(fields.datetime.now() - timedelta(days=365))
        #TODO: state = done?
        domain = [('state', '=', 'done'), ('product_id', 'in', self.ids), ('date_planned_start', '>', date_from)]
        read_group_res = self.env['mrp.production']._read_group(domain, ['product_id', 'product_uom_qty'], ['product_id'])
        mapped_data = dict([(data['product_id'][0], data['product_uom_qty']) for data in read_group_res])
        for product in self:
            if not product.id:
                product.mrp_product_qty = 0.0
                continue
            product.mrp_product_qty = float_round(mapped_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)

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
            ratios_virtual_available = []
            ratios_qty_available = []
            ratios_incoming_qty = []
            ratios_outgoing_qty = []
            ratios_free_qty = []
            for bom_line, bom_line_data in bom_sub_lines:
                component = bom_line.product_id.with_context(mrp_compute_quantities=qties).with_prefetch(prefetch_component_ids)
                if component.type != 'product' or float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                    # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                    # to avoid a division by zero. The same logic is applied to non-storable products as those
                    # products have 0 qty available.
                    continue
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, round=False, raise_if_failure=False)
                if not qty_per_kit:
                    continue
                rounding = component.uom_id.rounding
                component_res = (
                    qties.get(component.id)
                    if component.id in qties
                    else {
                        "virtual_available": float_round(component.virtual_available, precision_rounding=rounding),
                        "qty_available": float_round(component.qty_available, precision_rounding=rounding),
                        "incoming_qty": float_round(component.incoming_qty, precision_rounding=rounding),
                        "outgoing_qty": float_round(component.outgoing_qty, precision_rounding=rounding),
                        "free_qty": float_round(component.free_qty, precision_rounding=rounding),
                    }
                )
                ratios_virtual_available.append(component_res["virtual_available"] / qty_per_kit)
                ratios_qty_available.append(component_res["qty_available"] / qty_per_kit)
                ratios_incoming_qty.append(component_res["incoming_qty"] / qty_per_kit)
                ratios_outgoing_qty.append(component_res["outgoing_qty"] / qty_per_kit)
                ratios_free_qty.append(component_res["free_qty"] / qty_per_kit)
            if bom_sub_lines and ratios_virtual_available:  # Guard against all cnsumable bom: at least one ratio should be present.
                res[product.id] = {
                    'virtual_available': min(ratios_virtual_available) // 1,
                    'qty_available': min(ratios_qty_available) // 1,
                    'incoming_qty': min(ratios_incoming_qty) // 1,
                    'outgoing_qty': min(ratios_outgoing_qty) // 1,
                    'free_qty': min(ratios_free_qty) // 1,
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
            'default_product_id': self.ids[0],
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
            res['context']['single_product'] = False
            res['context'].pop('default_product_tmpl_id', None)
        return res

    def action_compute_bom_days(self):
        bom_by_products = self.env['mrp.bom']._bom_find(self)
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        for product in self:
            bom_data = self.env['report.mrp.report_bom_structure'].with_context(minimized=True)._get_bom_data(bom_by_products[product], warehouse, product, ignore_stock=True)
            availability_delay = bom_data.get('resupply_avail_delay')
            product.days_to_prepare_mo = availability_delay - bom_data.get('lead_time', 0) if availability_delay else 0

    def _match_all_variant_values(self, product_template_attribute_value_ids):
        """ It currently checks that all variant values (`product_template_attribute_value_ids`)
        are in the product (`self`).

        If multiple values are encoded for the same attribute line, only one of
        them has to be found on the variant.
        """
        self.ensure_one()
        if not product_template_attribute_value_ids:
            return True
        for _, iter_ptav in groupby(product_template_attribute_value_ids, lambda ptav: ptav.attribute_line_id):
            if not any(ptav in self.product_template_attribute_value_ids for ptav in iter_ptav):
                return False
        return True

    def _count_returned_sn_products(self, sn_lot):
        res = self.env['stock.move.line'].search_count([
            ('lot_id', '=', sn_lot.id),
            ('qty_done', '=', 1),
            ('state', '=', 'done'),
            ('production_id', '=', False),
            ('location_id.usage', '=', 'production'),
            ('move_id.unbuild_id', '!=', False),
        ])
        return super()._count_returned_sn_products(sn_lot) + res

    def _search_qty_available_new(self, operator, value, lot_id=False, owner_id=False, package_id=False):
        '''extending the method in stock.product to take into account kits'''
        product_ids = super(ProductProduct, self)._search_qty_available_new(operator, value, lot_id, owner_id, package_id)
        kit_boms = self.env['mrp.bom'].search([('type', "=", 'phantom')])
        kit_products = self.env['product.product']
        for kit in kit_boms:
            if kit.product_id:
                kit_products |= kit.product_id
            else:
                kit_products |= kit.product_tmpl_id.product_variant_ids
        for product in kit_products:
            if OPERATORS[operator](product.qty_available, value):
                product_ids.append(product.id)
        return list(set(product_ids))
