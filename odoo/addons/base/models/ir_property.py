# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import api, fields, models, _
from odoo.tools import ormcache

TYPE2FIELD = {
    'char': 'value_text',
    'float': 'value_float',
    'boolean': 'value_integer',
    'integer': 'value_integer',
    'text': 'value_text',
    'binary': 'value_binary',
    'many2one': 'value_integer',
    'date': 'value_datetime',
    'datetime': 'value_datetime',
    'selection': 'value_text',
}

TYPE2CLEAN = {
    'boolean': bool,
    'integer': lambda val: val or False,
    'float': lambda val: val or False,
    'char': lambda val: val or False,
    'text': lambda val: val or False,
    'selection': lambda val: val or False,
    'binary': lambda val: val or False,
    'date': lambda val: val.date() if val else False,
    'datetime': lambda val: val or False,
}

class MysteryField(fields.Field):
    type = 'mystery'

class Property(models.Model):
    _name = 'ir.property'
    _description = 'Company Property'

    res_id = fields.Integer(string='Resource', index=True, help="If 0, acts as a default value for new resources", required=True, default=0)
    company_id = fields.Many2one('res.company', string='Company', index=True)

    fields_id = fields.Many2one('ir.model.fields', string='Field', ondelete='cascade', required=True, index=True)
    name = fields.Char(store=True, related='fields_id.name', index=True)
    type = fields.Selection(store=True, readonly=True, related='fields_id.ttype', index=True)
    model = fields.Char(store=True, readonly=True, related='fields_id.model', index=True)

    value_float = fields.Float()
    value_integer = fields.Integer()
    value_text = fields.Text()  # will contain (char, text)
    value_binary = fields.Binary()
    value_datetime = fields.Datetime()

    value = MysteryField(compute='_compute_value', inverse='_set_value')

    @api.depends('type', 'value_float', 'value_integer', 'value_text', 'value_binary', 'value_datetime', 'fields_id.relation')
    def _compute_value(self):
        for prop in self:
            prop.value = False
            prop_type = prop.type

            if prop_type in ('char', 'text', 'selection'):
                prop.value = prop.value_text
            elif prop_type == 'float':
                prop.value = prop.value_float
            elif prop_type == 'boolean':
                prop.value = bool(prop.value_integer)
            elif prop_type == 'integer':
                prop.value = prop.value_integer
            elif prop_type == 'binary':
                prop.value = prop.value_binary
            elif prop_type == 'many2one':
                m = self.env[prop.fields_id.relation]
                if not prop.value_integer:
                    prop.value = m
                else:
                    prop.value = m.browse(prop.value_integer).exists()
            elif prop_type == 'datetime':
                prop.value = prop.value_datetime
            elif prop_type == 'date':
                if prop.value_datetime:
                    prop.value = fields.Date.to_string(fields.Datetime.from_string(prop.value_datetime))

    def _set_value(self):
        for prop in self:
            val = prop.value
            if prop.type == 'date' and isinstance(val, datetime.date):
                val = datetime.datetime.combine(val, datetime.time())
            prop[TYPE2FIELD[prop.type]] = val

    @api.multi
    def write(self, values):
        # if any of the records we're writing on has a res_id=0 *or*
        # we're writing a res_id=0 on any record
        default_set = False
        if self._ids:
            self.env.cr.execute(
                'SELECT EXISTS (SELECT 1 FROM ir_property WHERE id in %s AND res_id = 0)', [self._ids])
            default_set = self.env.cr.rowcount == 1 or any(
                v.get('res_id') == 0
                for v in values
            )
        r = super(Property, self).write(values)
        if default_set:
            self.clear_caches()
        return r

    @api.model_create_multi
    def create(self, vals_list):
        created_default = any(not v.get('res_id') for v in vals_list)
        r = super(Property, self).create(vals_list)
        if created_default:
            self.clear_caches()
        return r

    @api.multi
    def unlink(self):
        default_deleted = False
        if self._ids:
            self.env.cr.execute(
                'SELECT EXISTS (SELECT 1 FROM ir_property WHERE id in %s AND res_id = 0)',
                [self._ids]
            )
            default_deleted = self.env.cr.rowcount == 1
        r = super().unlink()
        if default_deleted:
            self.clear_caches()
        return r
    @api.model
    def get(self, name, model, res_id=False):
        if not res_id:
            t, v = self._get_default_property(name, model)
            if not v or t != 'many2one':
                return v
            return self.env[v[0]].browse(v[1])

        p = self._get_property(name, model, res_id=res_id)
        if p:
            return p.value
        return False

    # only cache Property.get(res_id=False) as that's
    # sub-optimally, we can only call _company_default_get without a field
    # unless we want to create a more complete helper which does the
    # returning-a-company-id-from-a-model-and-name
    COMPANY_KEY = "self.env.context.get('force_company') or self.env['res.company']._company_default_get(model).id"
    @ormcache(COMPANY_KEY, 'name', 'model')
    def _get_default_property(self, name, model):
        prop = self._get_property(name, model, res_id=0)
        if not prop:
            return None, False
        v = prop.value
        if prop.type != 'many2one':
            return prop.type, v
        return 'many2one', v and (v._name, v.id)

    def _get_property(self, name, model, res_id):
        domain = self._get_domain(name, model)
        if domain is not None:
            domain = [('res_id', '=', res_id)] + domain
            #make the search with company_id asc to make sure that properties specific to a company are given first
            return self.search(domain, limit=1, order='company_id')
        return self.browse(())

    def _get_domain(self, prop_name, model):
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (prop_name, model))
        res = self._cr.fetchone()
        if not res:
            return None
        company_id = self._context.get('force_company') or self.env['res.company']._company_default_get(model, res[0]).id
        return [('fields_id', '=', res[0]), ('company_id', 'in', [company_id, False])]

    @api.model
    def get_multi(self, name, model, ids):
        """ Read the property field `name` for the records of model `model` with
            the given `ids`, and return a dictionary mapping `ids` to their
            corresponding value.
        """
        if not ids:
            return {}

        field = self.env[model]._fields[name]
        field_id = self.env['ir.model.fields']._get(model, name).id
        company_id = (
            self._context.get('force_company')
            or self.env['res.company']._company_default_get(model, field_id).id
        )

        if field.type == 'many2one':
            comodel = self.env[field.comodel_name]
            # left join to check that the record linked through value_intger
            # exists, and return NULL otherwise
            query = """
                SELECT p.res_id, r.id
                FROM ir_property p
                LEFT JOIN {} r ON (p.value_integer = r.id)
                WHERE p.fields_id=%s
                  AND (p.company_id=%s OR p.company_id IS NULL)
                  AND (p.res_id IN %s OR p.res_id = 0)
                ORDER BY p.company_id NULLS FIRST 
            """.format(comodel._table)
            clean = comodel.browse

        elif field.type in TYPE2FIELD:
            query = """
                SELECT p.res_id, p.{}
                FROM ir_property p
                WHERE p.fields_id=%s
                    AND (p.company_id=%s OR p.company_id IS NULL)
                    AND (p.res_id IN %s OR p.res_id = 0)
                ORDER BY p.company_id NULLS FIRST
            """.format(TYPE2FIELD[field.type])
            clean = TYPE2CLEAN[field.type]

        else:
            return dict.fromkeys(ids, False)

        # retrieve values
        cr = self.env.cr
        result = {}
        for sub_ids in cr.split_for_in_conditions(ids):
            cr.execute(query, [field_id, company_id, sub_ids])
            result.update(cr.fetchall())

        # remove default value, add missing values, and format them
        default = result.pop(0, None)
        for id in ids:
            result[id] = clean(result.get(id, default))
        return result

    @api.model
    def set_multi(self, name, model, values, default_value=None):
        """ Assign the property field `name` for the records of model `model`
            with `values` (dictionary mapping record ids to their value).
            If the value for a given record is the same as the default
            value, the property entry will not be stored, to avoid bloating
            the database.
            If `default_value` is provided, that value will be used instead
            of the computed default value, to determine whether the value
            for a record should be stored or not.
        """
        def clean(value):
            return value.id if isinstance(value, models.BaseModel) else value

        if not values:
            return

        if default_value is None:
            domain = self._get_domain(name, model)
            if domain is None:
                raise Exception()
            # retrieve the default value for the field
            default_value = clean(self.get(name, model))

        # retrieve the properties corresponding to the given record ids
        self._cr.execute("SELECT id FROM ir_model_fields WHERE name=%s AND model=%s", (name, model))
        field_id = self._cr.fetchone()[0]
        company_id = self.env.context.get('force_company') or self.env['res.company']._company_default_get(model, field_id).id
        props = self.search([
            ('fields_id', '=', field_id),
            ('company_id', '=', company_id),
            ('res_id', 'in', list(values)),
        ])

        cleaned = {k: clean(v) for k, v in values.items()}

        # modify existing properties
        for prop in props:
            value = cleaned[prop.res_id]
            if value == default_value:
                # avoid prop.unlink(), as it clears the record cache that can
                # contain the value of other properties to set on record!
                prop.check_access_rights('unlink')
                prop.check_access_rule('unlink')
                self._cr.execute("DELETE FROM ir_property WHERE id=%s", [prop.id])
            elif value != clean(prop.value):
                prop.write({'value': value})

        # create new properties for records that do not have one yet
        vals_list = []
        for id, value in cleaned.items():
            if value != default_value:
                vals_list.append({
                    'fields_id': field_id,
                    'company_id': company_id,
                    'res_id': id,
                    'name': name,
                    'value': value,
                    'type': self.env[model]._fields[name].type,
                })
        self.create(vals_list)

    @api.model
    def search_multi(self, name, model, operator, value):
        """ Return a domain for the records that match the given condition. """
        default_matches = False
        include_zero = False

        field = self.env[model]._fields[name]
        if field.type == 'many2one':
            comodel = field.comodel_name
            if operator == "=":
                # if searching properties not set, search those not in those set
                if not value:
                    default_matches = True
            elif operator in ('=like', '=ilike', 'like', 'not like', 'ilike', 'not ilike'):
                # most probably inefficient... but correct
                target = self.env[comodel]
                target_names = target.name_search(value, operator=operator, limit=None)
                target_ids = [n[0] for n in target_names]
                operator, value = 'in', target_ids
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
            elif value < 0 and operator == '>':
                operator = '<='
                include_zero = True
            elif value >= 0 and operator == '<=':
                operator = '>'
                include_zero = True
            elif value > 0 and operator == '<':
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
                good_ids.append(prop.res_id)
            else:
                default_matches = True

        if include_zero:
            return [('id', 'not in', good_ids)]
        elif default_matches:
            # exclude all records with a property that does not match
            all_ids = self.search(domain + [('res_id', '!=', 0)]).mapped('res_id')
            bad_ids = list(set(all_ids) - set(good_ids))
            return [('id', 'not in', bad_ids)]
        else:
            return [('id', 'in', good_ids)]
