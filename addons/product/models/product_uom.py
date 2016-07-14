# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import time

import openerp
from openerp import api, tools, SUPERUSER_ID
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import psycopg2

import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round, float_compare
from openerp.exceptions import UserError
from openerp.exceptions import except_orm


class product_uom_categ(osv.osv):
    _name = 'product.uom.categ'
    _description = 'Product uom categ'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class product_uom(osv.osv):
    _name = 'product.uom'
    _description = 'Product Unit of Measure'

    def _compute_factor_inv(self, factor):
        return factor and (1.0 / factor) or 0.0

    def _factor_inv(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for uom in self.browse(cr, uid, ids, context=context):
            res[uom.id] = self._compute_factor_inv(uom.factor)
        return res

    def _factor_inv_write(self, cr, uid, id, name, value, arg, context=None):
        return self.write(cr, uid, id, {'factor': self._compute_factor_inv(value)}, context=context)

    def name_create(self, cr, uid, name, context=None):
        """ The UoM category and factor are required, so we'll have to add temporary values
            for imported UoMs """
        if not context:
            context = {}
        uom_categ = self.pool.get('product.uom.categ')
        values = {self._rec_name: name, 'factor': 1}
        # look for the category based on the english name, i.e. no context on purpose!
        # TODO: should find a way to have it translated but not created until actually used
        if not context.get('default_category_id'):
            categ_misc = 'Unsorted/Imported Units'
            categ_id = uom_categ.search(cr, uid, [('name', '=', categ_misc)])
            if categ_id:
                values['category_id'] = categ_id[0]
            else:
                values['category_id'] = uom_categ.name_create(
                    cr, uid, categ_misc, context=context)[0]
        uom_id = self.create(cr, uid, values, context=context)
        return self.name_get(cr, uid, [uom_id], context=context)[0]

    def create(self, cr, uid, data, context=None):
        if 'factor_inv' in data:
            if data['factor_inv'] != 1:
                data['factor'] = self._compute_factor_inv(data['factor_inv'])
            del(data['factor_inv'])
        return super(product_uom, self).create(cr, uid, data, context)

    _order = "name"
    _columns = {
        'name': fields.char('Unit of Measure', required=True, translate=True),
        'category_id': fields.many2one('product.uom.categ', 'Unit of Measure Category', required=True, ondelete='cascade',
            help="Conversion between Units of Measure can only occur if they belong to the same category. The conversion will be made based on the ratios."),
        'factor': fields.float('Ratio', required=True, digits=0, # force NUMERIC with unlimited precision
            help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n'\
                    '1 * (reference unit) = ratio * (this unit)'),
        'factor_inv': fields.function(_factor_inv, digits=0, # force NUMERIC with unlimited precision
            fnct_inv=_factor_inv_write,
            string='Bigger Ratio',
            help='How many times this Unit of Measure is bigger than the reference Unit of Measure in this category:\n'\
                    '1 * (this unit) = ratio * (reference unit)', required=True),
        'rounding': fields.float('Rounding Precision', digits=0, required=True,
            help="The computed quantity will be a multiple of this value. "\
                 "Use 1.0 for a Unit of Measure that cannot be further split, such as a piece."),
        'active': fields.boolean('Active', help="Uncheck the active field to disable a unit of measure without deleting it."),
        'uom_type': fields.selection([('bigger','Bigger than the reference Unit of Measure'),
                                      ('reference','Reference Unit of Measure for this category'),
                                      ('smaller','Smaller than the reference Unit of Measure')],'Type', required=1),
    }

    _defaults = {
        'active': 1,
        'rounding': 0.01,
        'factor': 1,
        'uom_type': 'reference',
        'factor': 1.0,
    }

    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!')
    ]

    @api.cr_uid
    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP'):
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        return self._compute_qty_obj(cr, uid, from_unit, qty, to_unit, round=round, rounding_method=rounding_method)

    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', context=None):
        if context is None:
            context = {}
        if from_unit.category_id.id != to_unit.category_id.id:
            if context.get('raise-exception', True):
                raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (from_unit.name,to_unit.name))
            else:
                return qty
        amount = qty/from_unit.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False):
        if (not from_uom_id or not price or not to_uom_id
                or (to_uom_id == from_uom_id)):
            return price
        from_unit, to_unit = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if from_unit.category_id.id != to_unit.category_id.id:
            return price
        amount = price * from_unit.factor
        if to_uom_id:
            amount = amount / to_unit.factor
        return amount

    def onchange_type(self, cr, uid, ids, value):
        if value == 'reference':
            return {'value': {'factor': 1, 'factor_inv': 1}}
        return {}
