# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ProductUomCateg(models.Model):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'

    name = fields.Char(required=True, translate=True)


class ProductUom(models.Model):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'
    _order = "name"

    name = fields.Char(string='Unit of Measure', required=True, translate=True)
    category_id = fields.Many2one('product.uom.categ', string='Unit of Measure Category', required=True, ondelete='cascade',
        help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios.")
    factor = fields.Float(string='Ratio', required=True, digits=0,  # force NUMERIC with unlimited precision
        help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                '1 * (reference unit) = ratio * (this unit)', default=1)
    factor_inv = fields.Float(compute='_compute_factor_inv', digits=0,  # force NUMERIC with unlimited precision
        inverse='_compute_factor_inv_write', string='Bigger Ratio',
        help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category:\n'\
                '1 * (this unit) = ratio * (reference unit)', required=True)
    rounding = fields.Float(string='Rounding Precision', digits=0, required=True,
        help="The computed quantity will be a multiple of this value. "\
             "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece.", default=0.01)
    active = fields.Boolean(help="By unchecking the active field you can disable a unit of measure without deleting it.", default=True)
    uom_type = fields.Selection([('bigger', 'Bigger than the reference Unit of Measure'),
                                  ('reference', 'Reference Unit of Measure for this category'),
                                  ('smaller', 'Smaller than the reference Unit of Measure')], string='Type', required=True, default='reference')

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!')
    ]

    def _get_factor_inv(self, factor):
        return factor and (1.0 / factor) or 0.0

    @api.depends('factor')
    def _compute_factor_inv(self):
        for uom in self:
            uom.factor_inv = self._get_factor_inv(uom.factor)

    def _compute_factor_inv_write(self):
        for uom in self:
            uom.factor = self._get_factor_inv(uom.factor)

    @api.model
    def name_create(self, name):
        """ The UoM category and factor are required, so we'll have to add temporary values
             for imported UoMs """

        ProductUomCateg = self.env['product.uom.categ']
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        categ_misc = 'Unsorted/Imported Units'
        categ_id = ProductUomCateg.search([('name', '=', categ_misc)], limit=1).id
        if not categ_id:
            categ_id, _ = ProductUomCateg.name_create(categ_misc)
        product_uom = self.create({self._rec_name: name,
                                        'category_id': categ_id,
                                        'factor': 1})
        return product_uom.name_get()[0]

    @api.v7
    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP'):
        from_uom = self.browse(cr, uid, from_uom_id)
        return from_uom._compute_qty(qty, to_uom_id=to_uom_id, round=round, rounding_method=rounding_method)

    @api.v8
    def _compute_qty(self, qty, to_uom_id=False, round=True, rounding_method='UP'):
        if not self or not qty or not to_uom_id:
            return qty
        to_uom = self.browse(to_uom_id)
        if to_uom == self:
            from_unit, to_unit = to_uom, self
        else:
            from_unit, to_unit = self, to_uom
        return from_unit._compute_qty_obj(qty, to_unit, round=round, rounding_method=rounding_method)

    @api.v7
    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', context=None):
        return from_unit._compute_qty_obj(qty, to_unit, round=round, rounding_method=rounding_method)

    @api.v8
    def _compute_qty_obj(self, qty, to_unit, round=True, rounding_method='UP'):
        if self.category_id != to_unit.category_id:
            if self.env.context.get('raise-exception', True):
                raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (self.name, to_unit.name))
            else:
                return qty
        amount = qty/self.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount

    @api.v7
    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        from_unit = self.browse(cr, uid, from_uom_id)
        return from_unit._compute_price(price, to_uom_id=to_uom_id)

    @api.v8
    def _compute_price(self, price, to_uom_id=False):
        if (not price or not to_uom_id
                or (to_uom_id == self.id)):
            return price
        to_unit = self.browse(to_uom_id)
        if self.category_id != to_unit.category_id:
            return price
        amount = (price * self.factor) / to_unit.factor
        return amount

    @api.onchange('uom_type')
    def onchange_type(self):
        if self.uom_type == 'reference':
            self.factor = 1
            self.factor_inv = 1

    @api.model
    def create(self, vals):
        if 'factor_inv' in vals:
            if vals['factor_inv'] != 1:
                vals['factor'] = self._get_factor_inv(vals['factor_inv'])
            del(vals['factor_inv'])
        return super(ProductUom, self).create(vals)
