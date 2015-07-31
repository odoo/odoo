# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.addons.product import _common
from openerp.exceptions import UserError


class MrpBom(models.Model):
    """
    Defines bills of material for a product.
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit = ['mail.thread']
    _order = "sequence"

    def _get_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id')

    name = fields.Char()
    code = fields.Char(string='Reference', size=16)
    active = fields.Boolean(string='Active', default=True, help="If the active field is set to False, it will allow you to hide the bills of material without removing it.")
    type = fields.Selection([('normal', 'Manufacture this product'), ('phantom', 'Ship this product as a set of components (kit)')], string='BoM Type', required=True, default='normal',
                help= "Set: When processing a sales order for this product, the delivery order will contain the raw materials, instead of the finished product.")
    position= fields.Char(string='Internal Reference', help="Reference to a position in an external plan.")
    product_tmpl_id = fields.Many2one('product.template', string='Product', domain="[('type', '!=', 'service')]", required=True)
    product_id = fields.Many2one('product.product', string='Product Variant',
            domain="['&', ('product_tmpl_id','=',product_tmpl_id), ('type','!=', 'service')]",
            help="If a product variant is defined the BOM is available only for this product.")
    bom_line_ids = fields.One2many('mrp.bom.line', 'bom_id', string='BoM Lines', copy=True)
    product_qty = fields.Float(string='Product Quantity', required=True, default=1.0, digits_compute=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Many2one('product.uom', default=_get_uom_id, string='Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    date_start = fields.Date(string='Valid From', help="Validity of this BoM. Keep empty if it's always valid.")
    date_stop = fields.Date(string='Valid Until', help="Validity of this BoM. Keep empty if it's always valid.")
    sequence = fields.Integer(string='Sequence', help="Gives The sequence order when displaying a list of bills of material.")
    routing_id = fields.Many2one('mrp.routing', string='Work Order Operations', help="The list of operations (list of work centers) to produce the finished product. "\
            "The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning.")
    product_rounding = fields.Float(string='Product Rounding', help="Rounding applied on the product quantity.")
    product_efficiency = fields.Float(string='Manufacturing Efficiency', default=1.0, required=True, help="A factor of 0.9 means a loss of 10% during the production process.")
    property_ids = fields.Many2many('mrp.property', string='Properties')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('mrp.bom'))

    @api.model
    def _bom_find(self, product_tmpl_id=None, product_id=None, properties=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        today_date = fields.date.today()
        if properties is None:
            properties = []
        if product_id:
            if not product_tmpl_id:
                product_tmpl_id = self.env['product.product'].browse(product_id).product_tmpl_id.id
            domain = ['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        elif product_tmpl_id:
            domain = [('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        if self.env.context.get('company_id'):
            domain = domain + [('company_id', '=', self.env.context['company_id'])]
        domain = domain + [ '|', ('date_start', '=', False), ('date_start', '<=', today_date),
                            '|', ('date_stop', '=', False), ('date_stop', '>=', today_date)]
        # order to prioritize bom with product_id over the one without
        bom_ids = self.search(domain, order='sequence, product_id')
        # Search a BoM which has all properties specified, or if you can not find one, you could
        # pass a BoM without any properties with the smallest sequence
        bom_empty_prop = False
        for bom in bom_ids:
            if not set(map(int, bom.property_ids or [])) - set(properties or []):
                if not properties or bom.property_ids:
                    return bom.id
                elif not bom_empty_prop:
                    bom_empty_prop = bom.id
        return bom_empty_prop

    @api.model
    def _skip_bom_line(self, line, product):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control.
        @param line: BoM line.
        @param product: Selected product produced.
        @return: True or False
        """
        if line.date_start and line.date_start > fields.Date.today() or line.date_stop and line.date_stop < fields.Date.today():
            return True
        # all bom_line_id variant values must be in the product
        if line.attribute_value_ids:
            if not product or (set(map(int, line.attribute_value_ids or [])) - set(map(int, product.attribute_value_ids))):
                return True
        return False

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

        master_bom = master_bom or bom


        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            factor = _common.ceiling(factor, product_rounding)
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)

        result = []
        result2 = []

        routing = (routing_id and self.env['mrp.routing'].browse(routing_id)) or bom.routing_id or False
        if routing:
            for wc_use in routing.workcenter_lines:
                wc = wc_use.workcenter_id
                d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                mult = (d + (m and 1.0 or 0.0))
                cycle = mult * wc_use.cycle_nbr
                result2.append({
                    'name': tools.ustr(wc_use.name) + ' - ' + tools.ustr(bom.product_tmpl_id.name_get()[0][1]),
                    'workcenter_id': wc.id,
                    'sequence': level + (wc_use.sequence or 0),
                    'cycle': cycle,
                    'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
                })

        for bom_line_id in bom.bom_line_ids:
            if self._skip_bom_line(bom_line_id, product):
                continue
            if set(map(int, bom_line_id.property_ids or [])) - set(properties or []):
                continue

            if previous_products and bom_line_id.product_id.product_tmpl_id.id in previous_products:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.name,bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            bom_id = self._bom_find(product_id=bom_line_id.product_id.id, properties=properties)

            #If BoM should not behave like PhantoM, just add the product, otherwise explode further
            if bom_line_id.type != "phantom" and (not bom_id or self.browse(bom_id).type != "phantom"):
                result.append({
                    'name': bom_line_id.product_id.name,
                    'product_id': bom_line_id.product_id.id,
                    'product_qty': quantity,
                    'product_uom': bom_line_id.product_uom.id,
                    'product_uos_qty': bom_line_id.product_uos and _factor(bom_line_id.product_uos_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding) or False,
                    'product_uos': bom_line_id.product_uos and bom_line_id.product_uos.id or False,
                })
            elif bom_id:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(bom_id)
                # We need to convert to units/UoM of chosen BoM
                factor2 = self.env['product.uom']._compute_qty(bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_explode(bom2, bom_line_id.product_id, quantity2, properties=properties,
                    level=level + 10, previous_products=all_prod, master_bom=master_bom)
                result = result + res[0]
                result2 = result2 + res[1]
            else:
                raise UserError(_('BoM "%s" contains a phantom BoM line but the product "%s" does not have any BoM defined.') % (master_bom.name,bom_line_id.product_id.name_get()[0][1]))

        return result, result2

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        default['name'] = self.name + _(' (copy)')
        return super(MrpBom, self).copy_data(default)[0]

    @api.onchange('product_uom')
    def onchange_uom(self):
        if not self.product_uom or not self.product_tmpl_id:
            return
        if self.product_uom.category_id.id != self.product_tmpl_id.uom_id.category_id.id:
            raise UserError(_('The Product Unit of Measure you chose has a different category than in the product form.'))
            self.product_uom = self.product_tmpl_id.uom_id.id

    @api.multi
    def unlink(self):
        if self.env['mrp.production'].search([('bom_id', 'in', self.ids), ('state', 'not in', ['done', 'cancel'])]):
            raise UserError(_('You can not delete a Bill of Material with running manufacturing orders.\nPlease close or cancel it first.'))
        return super(MrpBom, self).unlink()

    @api.onchange('product_tmpl_id', 'product_qty')
    def onchange_product_tmpl_id(self):
        """ Changes UoM and name if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if self.product_tmpl_id:
            self.name = self.product_tmpl_id.name
            self.product_uom = self.product_tmpl_id.uom_id.id


class MrpBomLine(models.Model):
    _name = 'mrp.bom.line'
    _order = "sequence"
    _rec_name = "product_id"

    def _get_uom_id(self):
        return self.env['product.uom'].search([], limit=1, order='id')

    @api.multi
    def _get_child_bom_lines(self):
        """If the BOM line refers to a BOM, return the ids of the child BOM lines"""
        for bom_line in self:
            bom_id = self.env['mrp.bom']._bom_find(
                product_tmpl_id=bom_line.product_id.product_tmpl_id.id,
                product_id=bom_line.product_id.id)
            if bom_id:
                child_bom = self.env['mrp.bom'].browse(bom_id)
                self.child_line_ids = [bom.id for bom in child_bom.bom_line_ids]
            else:
                self.child_line_ids = False

    type = fields.Selection([('normal', 'Normal'), ('phantom', 'Phantom')], string='BoM Line Type', required=True, default='normal',
            help="Phantom: this product line will not appear in the raw materials of manufacturing orders,"
                 "it will be directly replaced by the raw materials of its own BoM, without triggering"
                 "an extra manufacturing order.")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uos_qty = fields.Float(string='Product UOS Qty')
    product_uos = fields.Many2one('product.uom', string='Product UOS', help="Product UOS (Unit of Sale) is the unit of measurement for the invoicing and promotion of stock.")
    product_qty = fields.Float(string='Product Quantity', required=True, default=1.0, digits_compute=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, default=_get_uom_id,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    date_start = fields.Date(string='Valid From', help="Validity of component. Keep empty if it's always valid.")
    date_stop = fields.Date(string='Valid Until', help="Validity of component. Keep empty if it's always valid.")
    sequence = fields.Integer(default=1, help="Gives the sequence order when displaying.")
    routing_id = fields.Many2one('mrp.routing', string='Work Order Operations', help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production planning.")
    product_rounding = fields.Float(string='Product Rounding', help="Rounding applied on the product quantity.")
    product_efficiency = fields.Float(string='Manufacturing Efficiency', required=True, default=1.0, help="A factor of 0.9 means a loss of 10% within the production process.")
    property_ids = fields.Many2many('mrp.property', string='Properties')  # Not used
    bom_id = fields.Many2one('mrp.bom', string='Parent BoM', ondelete='cascade', select=True, required=True)
    attribute_value_ids = fields.Many2many('product.attribute.value', string='Variants', help="BOM Product Variants needed form apply this line.")
    child_line_ids = fields.One2many('mrp.bom.line', compute='_get_child_bom_lines', string='BOM lines of the referred bom')

    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>0)', 'All product quantities must be greater than 0.\n' \
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs !'),
    ]

    @api.model
    def create(self, values):
        if 'product_id' in values and not 'product_uom' in values:
            values['product_uom'] = self.env['product.product'].browse(values.get('product_id')).uom_id.id
        return super(MrpBomLine, self).create(values)

    @api.onchange('product_id')
    def onchange_uom(self):
        if not self.product_uom or not self.product_id:
            return
        if self.product_uom.category_id.id != self.product_id.uom_id.category_id.id:
            raise UserError(_('The Product Unit of Measure you chose has a different category than in the product form.'))
            self.product_uom = self.product_id.uom_id.id

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Changes UoM if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            self.product_uos_qty = 0
            self.product_uos = False

            if self.product_id.uos_id.id:
                self.product_uos_qty = self.product_qty * self.product_id.uos_coeff
                self.product_uos = self.product_id.uos_id.id
