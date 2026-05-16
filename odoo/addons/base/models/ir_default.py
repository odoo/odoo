# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import date

from odoo import api, fields, models, tools
from odoo.api import SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import SQL


class IrDefault(models.Model):
    """ User-defined default values for fields. """
    _name = 'ir.default'
    _description = 'Default Values'
    _rec_name = 'field_id'
    _allow_sudo_commands = False

    field_id = fields.Many2one('ir.model.fields', string="Field", required=True,
                               ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', index=True,
                              help="If set, action binding only applies for this user.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', index=True,
                                 help="If set, action binding only applies for this company")
    condition = fields.Char('Condition', help="If set, applies the default upon condition.")
    json_value = fields.Char('Default Value (JSON format)', required=True)

    @api.constrains('json_value', 'field_id')
    def _check_json_format(self):
        for record in self:
            model_name = record.sudo().field_id.model_id.model
            model = self.env[model_name]
            field = model._fields[record.field_id.name]
            try:
                value = json.loads(record.json_value)
                field.convert_to_cache(value, model)
            except json.JSONDecodeError:
                raise ValidationError(self.env._('Invalid JSON format in Default Value field.'))
            except Exception:  # noqa: BLE001
                raise ValidationError(self.env._("Invalid value in Default Value field. Expected type '%(field_type)s' for '%(model_name)s.%(field_name)s'.",
                                        field_type=record.field_id.ttype, model_name=model_name, field_name=record.field_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        # invalidate all company dependent fields since their fallback value in cache may be changed
        self.env.invalidate_all()
        self.env.registry.clear_cache()
        return super(IrDefault, self).create(vals_list)

    def write(self, vals):
        if self:
            # invalidate all company dependent fields since their fallback value in cache may be changed
            self.env.invalidate_all()
            self.env.registry.clear_cache()
        new_default = super().write(vals)
        self.check_access('write')
        return new_default

    def unlink(self):
        if self:
            # invalidate all company dependent fields since their fallback value in cache may be changed
            self.env.invalidate_all()
            self.env.registry.clear_cache()
        return super(IrDefault, self).unlink()

    @api.model
    def set(self, model_name, field_name, value, user_id=False, company_id=False, condition=False):
        """ Defines a default value for the given field. Any entry for the same
            scope (field, user, company) will be replaced. The value is encoded
            in JSON to be stored to the database.

            :param model_name:
            :param field_name:
            :param value:
            :param user_id: may be ``False`` for all users, ``True`` for the
                            current user, or any user id
            :param company_id: may be ``False`` for all companies, ``True`` for
                               the current user's company, or any company id
            :param condition: optional condition that restricts the
                              applicability of the default value; this is an
                              opaque string, but the client typically uses
                              single-field conditions in the form ``'key=val'``.
        """
        if user_id is True:
            user_id = self.env.uid
        if company_id is True:
            company_id = self.env.company.id

        # check consistency of model_name, field_name, and value
        try:
            model = self.env[model_name]
            field = model._fields[field_name]
            parsed = field.convert_to_cache(value, model)
            if field.type in ('date', 'datetime') and isinstance(value, date):
                value = field.to_string(value)
            json_value = json.dumps(value, ensure_ascii=False)
        except KeyError:
            raise ValidationError(self.env._("Invalid field %(model)s.%(field)s", model=model_name, field=field_name))
        except Exception:
            raise ValidationError(self.env._("Invalid value for %(model)s.%(field)s: %(value)s", model=model_name, field=field_name, value=value))
        if field.type == 'integer' and not (-2**31 < parsed < 2**31-1):
            raise ValidationError(self.env._("Invalid value for %(model)s.%(field)s: %(value)s is out of bounds (integers should be between -2,147,483,648 and 2,147,483,647)", model=model_name, field=field_name, value=value))

        # update existing default for the same scope, or create one
        field = self.env['ir.model.fields']._get(model_name, field_name)
        default = self.search([
            ('field_id', '=', field.id),
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
            ('condition', '=', condition),
        ], limit=1)
        if default:
            # Avoid clearing the cache if nothing changes
            if default.json_value != json_value:
                default.write({'json_value': json_value})
        else:
            self.create({
                'field_id': field.id,
                'user_id': user_id,
                'company_id': company_id,
                'condition': condition,
                'json_value': json_value,
            })
        return True

    @api.model
    def _get(self, model_name, field_name, user_id=False, company_id=False, condition=False):
        """ Return the default value for the given field, user and company, or
            ``None`` if no default is available.

            :param model_name:
            :param field_name:
            :param user_id: may be ``False`` for all users, ``True`` for the
                            current user, or any user id
            :param company_id: may be ``False`` for all companies, ``True`` for
                               the current user's company, or any company id
            :param condition: optional condition that restricts the
                              applicability of the default value; this is an
                              opaque string, but the client typically uses
                              single-field conditions in the form ``'key=val'``.
        """
        if user_id is True:
            user_id = self.env.uid
        if company_id is True:
            company_id = self.env.company.id

        field = self.env['ir.model.fields']._get(model_name, field_name)
        default = self.search([
            ('field_id', '=', field.id),
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
            ('condition', '=', condition),
        ], limit=1)
        return json.loads(default.json_value) if default else None

    @api.model
    @tools.ormcache('self.env.uid', 'self.env.company.id', 'model_name', 'condition')
    # Note about ormcache invalidation: it is not needed when deleting a field,
    # a user, or a company, as the corresponding defaults will no longer be
    # requested. It must only be done when a user's company is modified.
    def _get_model_defaults(self, model_name, condition=False):
        """ Return the available default values for the given model (for the
            current user), as a dict mapping field names to values.
        """
        cr = self.env.cr
        self.flush_model()
        query = """ SELECT f.name, d.json_value
                    FROM ir_default d
                    JOIN ir_model_fields f ON d.field_id=f.id
                    WHERE f.model=%s
                        AND (d.user_id IS NULL OR d.user_id=%s)
                        AND (d.company_id IS NULL OR d.company_id=%s)
                        AND {}
                    ORDER BY d.user_id, d.company_id, d.id
                """
        # self.env.company is empty when there is no user (controllers with auth=None)
        params = [model_name, self.env.uid, self.env.company.id or None]
        if condition:
            query = query.format("d.condition=%s")
            params.append(condition)
        else:
            query = query.format("d.condition IS NULL")
        cr.execute(query, params)
        result = {}
        for row in cr.fetchall():
            # keep the highest priority default for each field
            if row[0] not in result:
                result[row[0]] = json.loads(row[1])
        return result

    @api.model
    def discard_records(self, records):
        """ Discard all the defaults of many2one fields using any of the given
            records.
        """
        json_vals = [json.dumps(id) for id in records.ids]
        domain = [('field_id.ttype', '=', 'many2one'),
                  ('field_id.relation', '=', records._name),
                  ('json_value', 'in', json_vals)]
        return self.search(domain).unlink()

    @api.model
    def discard_values(self, model_name, field_name, values):
        """ Discard all the defaults for any of the given values. """
        field = self.env['ir.model.fields']._get(model_name, field_name)
        json_vals = [json.dumps(value, ensure_ascii=False) for value in values]
        domain = [('field_id', '=', field.id), ('json_value', 'in', json_vals)]
        return self.search(domain).unlink()

    @tools.ormcache('model_name', 'field_name')
    def _get_field_column_fallbacks(self, model_name, field_name):
        company_ids = self.env.execute_query(SQL('SELECT ARRAY_AGG(id) FROM res_company'))[0][0]
        field = self.env[model_name]._fields[field_name]
        self_super = self.with_user(SUPERUSER_ID)
        return json.dumps({
            id_: field.convert_to_column(
                self_super.with_company(id_)._get_model_defaults(model_name).get(field_name),
                self_super.with_company(id_)
            )
            for id_ in company_ids
        })

    def _evaluate_condition_with_fallback(self, model_name, field_expr, operator, value):
        """
        when the field value of the condition is company_dependent without
        customization, evaluate if its fallback value will be kept by
        the condition
        return True/False/None(for unknown)
        """
        field_name, _property_name = fields.parse_field_expr(field_expr)
        model = self.env[model_name]
        field = model._fields[field_name]
        fallback = field.get_company_dependent_fallback(model)
        try:
            record = model.new({field_name: field.convert_to_write(fallback, model)})
            return bool(record.filtered_domain(Domain(field_expr, operator, value)))
        except ValueError:
            return None
