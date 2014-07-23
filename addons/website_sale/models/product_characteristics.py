
from openerp.osv import osv, fields


class attributes(osv.Model):
    _name = "product.attribute"

    def _get_float_max(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        if ids:
            cr.execute("""
                SELECT attribute_id, MAX(value)
                FROM product_attribute_line
                WHERE attribute_id in (%s)
                GROUP BY attribute_id
            """ % ",".join(map(str, ids)))
            result.update(dict(cr.fetchall()))
        return result

    def _get_float_min(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        if ids:
            cr.execute("""
                SELECT attribute_id, MIN(value)
                FROM product_attribute_line
                WHERE attribute_id in (%s)
                GROUP BY attribute_id
            """ % ",".join(map(str, ids)))
            result.update(dict(cr.fetchall()))
        return result

    def _get_min_max(self, cr, uid, ids, context=None):
        result = {}
        for value in self.pool.get('product.attribute.line').browse(cr, uid, ids, context=context):
            if value.type == 'float':
                result[value.attribute_id.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Name', translate=True, required=True),
        'type': fields.selection([('distinct', 'Textual Value'), ('float', 'Numeric Value')], "Type", required=True),
        'value_ids': fields.one2many('product.attribute.value', 'attribute_id', 'Values'),
        'attr_product_ids': fields.one2many('product.attribute.line', 'attribute_id', 'Products'),

        'float_max': fields.function(_get_float_max, type='float', string="Max", store={
                'product.attribute.line': (_get_min_max, ['value','attribute_id'], 20),
            }),
        'float_min': fields.function(_get_float_min, type='float', string="Min", store={
                'product.attribute.line': (_get_min_max, ['value','attribute_id'], 20),
            }),
        'visible': fields.boolean('Display Filter on Website'),
    }
    _defaults = {
        'type': 'distinct',
        'visible': True,
    }

class attributes_value(osv.Model):
    _name = "product.attribute.value"
    _columns = {
        'name': fields.char('Value', translate=True, required=True),
        'attribute_id': fields.many2one('product.attribute', 'attribute', required=True),
        'atr_product_ids': fields.one2many('product.attribute.line', 'value_id', 'Products'),
    }

class attributes_product(osv.Model):
    _name = "product.attribute.line"
    _order = 'attribute_id, value_id, value'
    _rec_name = 'attribute_id'
    _columns = {
        'value': fields.float('Numeric Value'),
        'value_id': fields.many2one('product.attribute.value', 'Textual Value'),
        'attribute_id': fields.many2one('product.attribute', 'attribute', required=True),
        'product_tmpl_id': fields.many2one('product.template', 'Product', required=True),

        'type': fields.related('attribute_id', 'type', type='selection',
            selection=[('distinct', 'Distinct'), ('float', 'Float')], string='Type'),
    }

    def onchange_attribute_id(self, cr, uid, ids, attribute_id, context=None):
        attribute = self.pool.get('product.attribute').browse(cr, uid, attribute_id, context=context)
        return {'value': {'type': attribute.type, 'value_id': False, 'value': ''}}

class product_template(osv.Model):
    _inherit = "product.template"
    _columns = {
        'attribute_lines': fields.one2many('product.attribute.line', 'product_tmpl_id', 'Product attributes'),
    }
