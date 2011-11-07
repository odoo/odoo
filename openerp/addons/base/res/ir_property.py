# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from osv import osv,fields
from tools.misc import attrgetter
import time

# -------------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------------

class ir_property(osv.osv):
    _name = 'ir.property'

    def _models_field_get(self, cr, uid, field_key, field_value, context=None):
        get = attrgetter(field_key, field_value)
        obj = self.pool.get('ir.model.fields')
        ids = obj.search(cr, uid, [('view_load','=',1)], context=context)
        res = set()
        for o in obj.browse(cr, uid, ids, context=context):
            res.add(get(o))
        return list(res)

    def _models_get(self, cr, uid, context=None):
        return self._models_field_get(cr, uid, 'model', 'model_id.name', context)

    def _models_get2(self, cr, uid, context=None):
        return self._models_field_get(cr, uid, 'relation', 'relation', context)


    _columns = {
        'name': fields.char('Name', size=128, select=1),

        'res_id': fields.reference('Resource', selection=_models_get, size=128,
                                   help="If not set, acts as a default value for new resources", select=1),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'fields_id': fields.many2one('ir.model.fields', 'Field', ondelete='cascade', required=True, select=1),

        'value_float' : fields.float('Value'),
        'value_integer' : fields.integer_big('Value'), # will contain (int, bigint)
        'value_text' : fields.text('Value'), # will contain (char, text)
        'value_binary' : fields.binary('Value'),
        'value_reference': fields.reference('Value', selection=_models_get2, size=128),
        'value_datetime' : fields.datetime('Value'),

        'type' : fields.selection([('char', 'Char'),
                                   ('float', 'Float'),
                                   ('boolean', 'Boolean'),
                                   ('integer', 'Integer'),
                                   ('integer_big', 'Integer Big'),
                                   ('text', 'Text'),
                                   ('binary', 'Binary'),
                                   ('many2one', 'Many2One'),
                                   ('date', 'Date'),
                                   ('datetime', 'DateTime'),
                                  ],
                                  'Type',
                                  required=True,
                                  select=1),
    }

    _defaults = {
        'type': 'many2one',
    }

    def _update_values(self, cr, uid, ids, values):
        value = values.pop('value', None)
        if not value:
            return values

        prop = None
        type_ = values.get('type')
        if not type_:
            if ids:
                prop = self.browse(cr, uid, ids[0])
                type_ = prop.type
            else:
                type_ = self._defaults['type']

        type2field = {
            'char': 'value_text',
            'float': 'value_float',
            'boolean' : 'value_integer',
            'integer': 'value_integer',
            'integer_big': 'value_integer',
            'text': 'value_text',
            'binary': 'value_binary',
            'many2one': 'value_reference',
            'date' : 'value_datetime',
            'datetime' : 'value_datetime',
        }
        field = type2field.get(type_)
        if not field:
            raise osv.except_osv('Error', 'Invalid type')

        if field == 'value_reference':
            if isinstance(value, osv.orm.browse_record):
                value = '%s,%d' % (value._name, value.id)
            elif isinstance(value, (int, long)):
                field_id = values.get('fields_id')
                if not field_id:
                    if not prop:
                        raise ValueError()
                    field_id = prop.fields_id
                else:
                    field_id = self.pool.get('ir.model.fields').browse(cr, uid, field_id)

                value = '%s,%d' % (field_id.relation, value)

        values[field] = value
        return values


    def write(self, cr, uid, ids, values, context=None):
        return super(ir_property, self).write(cr, uid, ids, self._update_values(cr, uid, ids, values), context=context)

    def create(self, cr, uid, values, context=None):
        return super(ir_property, self).create(cr, uid, self._update_values(cr, uid, None, values), context=context)

    def get_by_record(self, cr, uid, record, context=None):
        if record.type in ('char', 'text'):
            return record.value_text
        elif record.type == 'float':
            return record.value_float
        elif record.type == 'boolean':
            return bool(record.value_integer)
        elif record.type in ('integer', 'integer_big'):
            return record.value_integer
        elif record.type == 'binary':
            return record.value_binary
        elif record.type == 'many2one':
            return record.value_reference
        elif record.type == 'datetime':
            return record.value_datetime
        elif record.type == 'date':
            if not record.value_datetime:
                return False
            return time.strftime('%Y-%m-%d', time.strptime(record.value_datetime, '%Y-%m-%d %H:%M:%S'))
        return False

    def get(self, cr, uid, name, model, res_id=False, context=None):
        domain = self._get_domain(cr, uid, name, model, context=context)
        if domain is not None:
            domain = [('res_id', '=', res_id)] + domain
            nid = self.search(cr, uid, domain, context=context)
            if not nid: return False
            record = self.browse(cr, uid, nid[0], context=context)
            return self.get_by_record(cr, uid, record, context=context)
        return False

    def _get_domain_default(self, cr, uid, prop_name, model, context=None):
        domain = self._get_domain(cr, uid, prop_name, model, context=context)
        if domain is None:
            return None
        return ['&', ('res_id', '=', False)] + domain

    def _get_domain(self, cr, uid, prop_name, model, context=None):
        context = context or {}
        cr.execute('select id from ir_model_fields where name=%s and model=%s', (prop_name, model))
        res = cr.fetchone()
        if not res:
            return None

        if 'force_company' in context and context['force_company']:
            cid = context['force_company']
        else:
            company = self.pool.get('res.company')
            cid = company._company_default_get(cr, uid, model, res[0], context=context)

        domain = ['&', ('fields_id', '=', res[0]),
                  '|', ('company_id', '=', cid), ('company_id', '=', False)]
        return domain

ir_property()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

