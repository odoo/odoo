# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import models, fields, _
from odoo.exceptions import UserError


class Base(models.AbstractModel):
    _inherit = 'base'

    def _valid_field_parameter(self, field, name):
        return name == 'sparse' or super()._valid_field_parameter(field, name)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    ttype = fields.Selection(selection_add=[
        ('serialized', 'serialized'),
    ], ondelete={'serialized': 'cascade'})
    serialization_field_id = fields.Many2one('ir.model.fields', string='Serialization Field',
        ondelete='cascade', domain="[('ttype','in',('json', 'serialized')), ('model_id', '=', model_id)]",
        help="If set, this field will be stored in the sparse structure of the "
             "serialization field, instead of having its own database column. "
             "This cannot be changed after creation.",
    )

    def write(self, vals):
        # Limitation: renaming a sparse field or changing the storing system is
        # currently not allowed
        if 'serialization_field_id' in vals or 'name' in vals:
            for field in self:
                if 'serialization_field_id' in vals and field.serialization_field_id.id != vals['serialization_field_id']:
                    raise UserError(_('Changing the storing system for field "%s" is not allowed.', field.name))
                if field.serialization_field_id and (field.name != vals['name']):
                    raise UserError(_('Renaming sparse field "%s" is not allowed', field.name))
        return super().write(vals)

    def _reflect_fields(self, model_names):
        super()._reflect_fields(model_names)

        # set 'serialization_field_id' on sparse fields; it is done here to
        # ensure that the serialized field is reflected already
        cr = self._cr

        # retrieve existing values
        query = """
            SELECT model, name, id, serialization_field_id
            FROM ir_model_fields
            WHERE model IN %s
        """
        cr.execute(query, [tuple(model_names)])
        existing = {row[:2]: row[2:] for row in cr.fetchall()}

        # determine updates, grouped by value
        updates = defaultdict(list)
        for model_name in model_names:
            for field_name, field in self.env[model_name]._fields.items():
                field_id, current_value = existing[(model_name, field_name)]
                try:
                    value = existing[(model_name, field.sparse)][0] if field.sparse else None
                except KeyError:
                    raise UserError(_(
                        'Serialization field "%(serialization_field)s" not found for sparse field %(sparse_field)s!',
                        serialization_field=field.sparse,
                        sparse_field=field,
                    ))
                if current_value != value:
                    updates[value].append(field_id)

        if not updates:
            return

        # update fields
        query = "UPDATE ir_model_fields SET serialization_field_id=%s WHERE id IN %s"
        for value, ids in updates.items():
            cr.execute(query, [value, tuple(ids)])

        records = self.browse(id_ for ids in updates.values() for id_ in ids)
        self.pool.post_init(records.modified, ['serialization_field_id'])

    def _instanciate_attrs(self, field_data):
        attrs = super()._instanciate_attrs(field_data)
        if attrs and field_data.get('serialization_field_id'):
            serialization_record = self.browse(field_data['serialization_field_id'])
            attrs['sparse'] = serialization_record.name
        return attrs
