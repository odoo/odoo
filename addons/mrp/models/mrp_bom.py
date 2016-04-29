# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class BoM(models.Model):
    """ Defines bills of material for a product. """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _order = "sequence"
    _rec_name = 'code'
    _inherit = ['mail.thread']

    def _get_default_product_uom(self):
        return self.env['product.uom'].search([], limit=1, order='id').id

    code = fields.Char('Reference')
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    type = fields.Selection([
        ('normal', 'Manufacture this product'),
        ('phantom', 'Ship this product as a set of components (kit)')],
        string='BoM Type', default='normal', required=True,
        help="Set: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product.")
    position = fields.Char('Internal Reference', help="Reference to a position in an external plan.")
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product',
        domain="[('type', 'in', ['product', 'consu'])]",
        required=True)
    product_id = fields.Many2one(
        'product.product', 'Product Variant',
        domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu'])]",
        help="If a product variant is defined the BOM is available only for this product.")
    bom_line_ids = fields.One2many('mrp.bom.line', 'bom_id', 'BoM Lines', copy=True)
    product_qty = fields.Float(
        'Product Quantity', default=1.0,
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        default=_get_default_product_uom, required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    date_start = fields.Date('Valid From', help="Validity of this BoM. Keep empty if it's always valid.")
    date_stop = fields.Date('Valid Until', help="Validity of this BoM. Keep empty if it's always valid.")
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of bills of material.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        help="The list of operations (list of work centers) to produce the finished product. "
             "The routing is mainly used to compute work center costs during operations and to "
             "plan future loads on work centers based on production planning.")
    product_rounding = fields.Float(
        'Product Rounding', default=0.0,
        help="Rounding applied on the product quantity.")
    product_efficiency = fields.Float(
        'Manufacturing Efficiency',
        default=1.0, required=True,
        help="A factor of 0.9 means a loss of 10% during the production process.")
    property_ids = fields.Many2many('mrp.property', string='Properties')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('mrp.bom'),
        required=True)

    @api.multi
    def name_get(self):
        return [(bom.id, '%s%s' % (bom.code and '[%s]' % bom.code or '', bom.product_tmpl_id.name)) for bom in self]

    @api.multi
    def unlink(self):
        if self.env['mrp.production'].search([('bom_id', 'in', self.ids), ('state', 'not in', ['done', 'cancel'])], limit=1):
            raise UserError(_('You can not delete a Bill of Material with running manufacturing orders.\nPlease close or cancel it first.'))
        return super(BoM, self).unlink()

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_uom or not self.product_tmpl_id:
            return res
        if self.product_uom.category_id != self.product_tmpl_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            self.product_uom = self.product_id.uom_id.id
        return res

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom = self.product_tmpl_id.uom_id.id

    @api.model
    @api.returns('self', lambda value: value.id)
    def _bom_find(self, product_tmpl_id=None, product_id=None, properties=None, company_id=False):
        """ Finds BoM for particular product and product uom. """
        if properties is None:
            properties = []

        domain = ['|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                  '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT))]
        if product_id:
            if not product_tmpl_id:
                product_tmpl_id = self.env['product.product'].browse(product_id).product_tmpl_id.id
            domain += ['|',
                       ('product_id', '=', product_id),
                       '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        elif product_tmpl_id:
            domain += [('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        if self._context.get('company_id', company_id):
            domain += [('company_id', '=', self._context.get('company_id', company_id))]
        # order to prioritize bom with product_id over the one without
        boms = self.search(domain, order='sequence, product_id')
        # Search a BoM which has all properties specified, or if you can not find one, you could
        # pass a BoM without any properties with the smallest sequence
        bom_empty_prop = self.env['mrp.bom']
        for bom in boms:
            if not set(bom.property_ids.ids) - set(properties):
                if not properties or bom.property_ids:
                    return bom
                elif not bom_empty_prop:
                    bom_empty_prop = bom
        return bom_empty_prop

    @api.multi
    def _prepare_wc_line(self, routing_workcenter, level=0, factor=1):
        workcenter = routing_workcenter.workcenter_id
        d, m = divmod(factor, routing_workcenter.workcenter_id.capacity_per_cycle)
        mult = (d + (m and 1.0 or 0.0))
        cycle = mult * routing_workcenter.cycle_nbr
        return {
            'name': tools.ustr(routing_workcenter.name) + ' - ' + tools.ustr(self.product_tmpl_id.name_get()[0][1]),
            'workcenter_id': workcenter.id,
            'sequence': level + (routing_workcenter.sequence or 0),
            'cycle': cycle,
            'hour': float(routing_workcenter.hour_nbr * mult + ((workcenter.time_start or 0.0) + (workcenter.time_stop or 0.0) + cycle * (workcenter.time_cycle or 0.0)) * (workcenter.time_efficiency or 100)),
        }

    @api.model
    def _prepare_consume_line(self, bom_line_id, quantity):
        return {
            'name': bom_line_id.product_id.name,
            'product_id': bom_line_id.product_id.id,
            'product_qty': quantity,
            'product_uom': bom_line_id.product_uom.id
        }

    @api.model
    def _bom_explode(self, bom, product, factor, properties=None, level=0, routing_id=False, previous_products=None, master_bom=None):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product template.
        @param product: Select a particular variant of the BoM. If False use BoM without variants.
        @param factor: Factor represents the quantity, but in UoM of the BoM, taking into account the numbers produced by the BoM
        @param properties: A List of properties Ids.
        @param level: Depth level to find BoM lines starts from 10.
        @param previous_products: List of product previously use by bom explore to avoid recursion
        @param master_bom: When recursion, used to display the name of the master bom
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        UoM = self.env["product.uom"]
        Routing = self.env['mrp.routing']
        master_bom = master_bom or bom

        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            if product_rounding:
                factor = tools.float_round(factor,
                                           precision_rounding=product_rounding,
                                           rounding_method='UP')
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)

        result = []
        result2 = []

        routing = (routing_id and Routing.browse(routing_id)) or bom.routing_id or False
        if routing:
            for wc_use in routing.workcenter_lines:
                result2.append(bom._prepare_wc_line(wc_use, level=level, factor=factor))

        for bom_line_id in bom.bom_line_ids:
            if bom_line_id._skip_bom_line(product):
                continue
            if set(map(int, bom_line_id.property_ids or [])) - set(properties or []):
                continue

            if previous_products and bom_line_id.product_id.product_tmpl_id.id in previous_products:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.code or "", bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            new_bom = self._bom_find(product_id=bom_line_id.product_id.id, properties=properties)

            # If BoM should not behave like kit, just add the product, otherwise explode further
            if not new_bom or new_bom.type != "phantom":
                result.append(self._prepare_consume_line(bom_line_id, quantity))
            else:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                # We need to convert to units/UoM of chosen BoM
                factor2 = UoM._compute_qty_obj(bom_line_id.product_uom, quantity, new_bom.product_uom)
                quantity2 = factor2 / new_bom.product_qty
                res = self._bom_explode(
                    new_bom, bom_line_id.product_id, quantity2,
                    properties=properties, level=level + 10, previous_products=all_prod, master_bom=master_bom)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2


class BoMLine(models.Model):
    _name = 'mrp.bom.line'
    _order = "sequence"
    _rec_name = "product_id"

    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True)
    product_qty = fields.Float(
        'Product Quantity', default=1.0,
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        default=lambda self: self.env['mrp.bom']._get_default_product_uom(),
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    date_start = fields.Date('Valid From', help="Validity of component. Keep empty if it's always valid.")
    date_stop = fields.Date('Valid Until', help="Validity of component. Keep empty if it's always valid.")
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    routing_id = fields.Many2one(
        'mrp.routing', 'Routing',
        help="The list of operations (list of work centers) to produce the finished product. The "
             "routing is mainly used to compute work center costs during operations and to plan "
             "future loads on work centers based on production planning.")
    product_rounding = fields.Float(
        'Product Rounding', default=0.0,
        help="Rounding applied on the product quantity.")
    product_efficiency = fields.Float(
        'Manufacturing Efficiency',
        default=1.0, required=True,
        help="A factor of 0.9 means a loss of 10% within the production process.")
    property_ids = fields.Many2many('mrp.property', string='Properties')  # Not used
    bom_id = fields.Many2one(
        'mrp.bom', 'Parent BoM',
        index=True, ondelete='cascade', required=True)
    attribute_value_ids = fields.Many2many(
        'product.attribute.value', string='Variants',
        help="BOM Product Variants needed form apply this line.")
    child_line_ids = fields.One2many(
        'mrp.bom.line', string="BOM lines of the referred bom",
        compute='_compute_child_line_ids')

    @api.one
    @api.depends('product_id')
    def _compute_child_line_ids(self):
        """ If the BOM line refers to a BOM, return the ids of the child BOM lines """
        if not self.product_id:
            self.child_line_ids = False
            return
        bom = self.env['mrp.bom']._bom_find(
            product_tmpl_id=self.product_id.product_tmpl_id.id,
            product_id=self.product_id.id)
        if bom:
            self.child_line_ids = bom.bom_line_ids.ids
        else:
            self.child_line_ids = False

    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)', 'All product quantities must be greater than 0.\n' \
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    @api.model
    def create(self, values):
        if 'product_id' in values and not values.get('product_uom'):
            values['product_uom'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        return super(BoMLine, self).create(values)

    @api.onchange('product_uom')
    def onchange_uom(self):
        res = {}
        if not self.product_uom or not self.product_id:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            self.product_uom = self.product_id.uom_id.id
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    def _skip_bom_line(self, product):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control. """
        if self.date_start and self.date_start > time.strftime(DEFAULT_SERVER_DATE_FORMAT) or \
                self.date_stop and self.date_stop < time.strftime(DEFAULT_SERVER_DATE_FORMAT):
            return True
        # all bom_line_id variant values must be in the product
        if self.attribute_value_ids:
            if not product or (set(self.attribute_value_ids.ids) - set(product.attribute_value_ids.ids)):
                return True
        return False
