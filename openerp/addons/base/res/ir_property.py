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

from operator import itemgetter
import time

from openerp import models, api
from openerp.osv import osv, orm, fields
from openerp.tools.misc import attrgetter

# -------------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------------

TYPE2FIELD = {
    'char': 'value_text',
    'float': 'value_float',
    'boolean': 'value_integer',
    'integer': 'value_integer',
    'text': 'value_text',
    'binary': 'value_binary',
    'many2one': 'value_reference',
    'date': 'value_datetime',
    'datetime': 'value_datetime',
    'selection': 'value_text',
}

class ir_property(osv.osv):
    _name = 'ir.property'

    _columns = {
        'name': fields.char('Name', select=1),

        'res_id': fields.char('Resource', help="If not set, acts as a default value for new resources", select=1),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'fields_id': fields.many2one('ir.model.fields', 'Field', ondelete='cascade', required=True, select=1),

        'value_float' : fields.float('Value'),
        'value_integer' : fields.integer('Value'),
        'value_text' : fields.text('Value'), # will contain (char, text)
        'value_binary' : fields.binary('Value'),
        'value_reference': fields.char('Value'),
        'value_datetime' : fields.datetime('Value'),

        'type' : fields.selection([('char', 'Char'),
                                   ('float', 'Float'),
                                   ('boolean', 'Boolean'),
                                   ('integer', 'Integer'),
                                   ('text', 'Text'),
                                   ('binary', 'Binary'),
                                   ('many2one', 'Many2One'),
                                   ('date', 'Date'),
                                   ('datetime', 'DateTime'),
                                   ('selection', 'Selection'),
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

        field = TYPE2FIELD.get(type_)
        if not field:
            raise osv.except_osv('Error', 'Invalid type')

        if field == 'value_reference':
            if isinstance(value, orm.BaseModel):
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
        if record.type in ('char', 'text', 'selection'):
            return record.value_text
        elif record.type == 'float':
            return record.value_float
        elif record.type == 'boolean':
            return bool(record.value_integer)
        elif record.type == 'integer':
            return record.value_integer
        elif record.type == 'binary':
            return record.value_binary
        elif record.type == 'many2one':
            if not record.value_reference:
                return False
            model, resource_id = record.value_reference.split(',')
            value = self.pool[model].browse(cr, uid, int(resource_id), context=context)
            return value.exists()
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
            #make the search with company_id asc to make sure that properties specific to a company are given first
            nid = self.search(cr, uid, domain, limit=1, order='company_id asc', context=context)
            if not nid: return False
            record = self.browse(cr, uid, nid[0], context=context)
            return self.get_by_record(cr, uid, record, context=context)
        return False

    def _get_domain(self, cr, uid, prop_name, model, context=None):
        context = context or {}
        cr.execute('select id from ir_model_fields where name=%s and model=%s', (prop_name, model))
        res = cr.fetchone()
        if not res:
            return None

        cid = context.get('force_company')
        if not cid:
            company = self.pool.get('res.company')
            cid = company._company_default_get(cr, uid, model, res[0], context=context)

        return [('fields_id', '=', res[0]), ('company_id', 'in', [cid, False])]

    @api.model
    def get_multi(self, name, model, ids):
        """ Read the property field `name` for the records of model `model` with
            the given `ids`, and return a dictionary mapping `ids` to their
            corresponding value.
        """
        if not ids:
            return {}

        domain = self._get_domain(name, model)
        if domain is None:
            return dict.fromkeys(ids, False)

        # retrieve the values for the given ids and the default value, too
        refs = {('%s,%s' % (model, id)): id for id in ids}
        refs[False] = False
        domain += [('res_id', 'in', list(refs))]

        # note: order by 'company_id asc' will return non-null values first
        props = self.search(domain, order='company_id asc')
        result = {}
        for prop in props:
            # for a given res_id, take the first property only
            id = refs.pop(prop.res_id, None)
            if id is not None:
                result[id] = self.get_by_record(prop)

        # set the default value to the ids that are not in result
        default_value = result.pop(False, False)
        for id in ids:
            result.setdefault(id, default_value)

        return result

    @api.model
    def set_multi(self, name, model, values):
        """ Assign the property field `name` for the records of model `model`
            with `values` (dictionary mapping record ids to their value).
        """
        def clean(value):
            return value.id if isinstance(value, models.BaseModel) else value

        if not values:
            return

        domain = self._get_domain(name, model)
        if domain is None:
            raise Exception()

        # retrieve the default value for the field
        default_value = clean(self.get(name, model))

        # retrieve the properties corresponding to the given record ids
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (name, model))
        field_id = self._cr.fetchone()[0]
        company_id = self.env.context.get('force_company') or self.env['res.company']._company_default_get(model, field_id)
        refs = {('%s,%s' % (model, id)): id for id in values}
        props = self.search([
            ('fields_id', '=', field_id),
            ('company_id', '=', company_id),
            ('res_id', 'in', list(refs)),
        ])

        # modify existing properties
        for prop in props:
            id = refs.pop(prop.res_id)
            value = clean(values[id])
            if value == default_value:
                prop.unlink()
            elif value != clean(prop.get_by_record(prop)):
                prop.write({'value': value})

        # create new properties for records that do not have one yet
        for ref, id in refs.iteritems():
            value = clean(values[id])
            if value != default_value:
                self.create({
                    'fields_id': field_id,
                    'company_id': company_id,
                    'res_id': ref,
                    'name': name,
                    'value': value,
                    'type': self.env[model]._fields[name].type,
                })

    @api.model
    def search_multi(self, name, model, operator, value):
        """ Return a domain for the records that match the given condition. """
        default_matches = False
        include_zero = False

        field = self.env[model]._fields[name]
        if field.type == 'many2one':
            comodel = field.comodel_name
            def makeref(value):
                return value and '%s,%s' % (comodel, value)
            if operator == "=":
                value = makeref(value)
                # if searching properties not set, search those not in those set
                if value is False:
                    default_matches = True
            elif operator in ('!=', '<=', '<', '>', '>='):
                value = makeref(value)
            elif operator in ('in', 'not in'):
                value = map(makeref, value)
            elif operator in ('=like', '=ilike', 'like', 'not like', 'ilike', 'not ilike'):
                # most probably inefficient... but correct
                target = self.env[comodel]
                target_names = target.name_search(value, operator=operator, limit=None)
                target_ids = map(itemgetter(0), target_names)
                operator, value = 'in', map(makeref, target_ids)
        elif field.type in ('integer', 'float'):
            # No record is created in ir.property if the field's type is float or integer with a value
            # equal to 0. Then to match with the records that are linked to a property field equal to 0,
            # the negation of the operator must be taken  to compute the goods and the domain returned
            # to match the searched records is just the opposite.
            if value == 0 and operator == '=':
                operator = '!='
                include_zero = True
            elif value <= 0 and operator == '>=':
                operator = '<'
                include_zero = True
            elif value <= 0 and operator == '>':
                operator = '<='
                include_zero = True
            elif value >= 0 and operator == '<=':
                operator = '>'
                include_zero = True
            elif value >= 0 and operator == '<':
                operator = '>='
                include_zero = True


        # retrieve the properties that match the condition
        domain = self._get_domain(name, model)
        if domain is None:
            raise Exception()
        props = self.search(domain + [(TYPE2FIELD[field.type], operator, value)])

        # retrieve the records corresponding to the properties that match
        good_ids = []
        for prop in props:
            if prop.res_id:
                res_model, res_id = prop.res_id.split(',')
                good_ids.append(int(res_id))
            else:
                default_matches = True

        if include_zero:
            return [('id', 'not in', good_ids)]
        elif default_matches:
            # exclude all records with a property that does not match
            all_ids = []
            props = self.search(domain + [('res_id', '!=', False)])
            for prop in props:
                res_model, res_id = prop.res_id.split(',')
                all_ids.append(int(res_id))
            bad_ids = list(set(all_ids) - set(good_ids))
            return [('id', 'not in', bad_ids)]
        else:
            return [('id', 'in', good_ids)]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
