# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    ttype = fields.Selection(selection_add=[('serialized', 'serialized')])
    serialization_field_id = fields.Many2one('ir.model.fields', string='Serialization Field',
        ondelete='cascade', domain="[('ttype','=','serialized'), ('model_id', '=', model_id)]",
        help="If set, this field will be stored in the sparse structure of the "
             "serialization field, instead of having its own database column. "
             "This cannot be changed after creation.",
    )

    @api.multi
    def write(self, vals):
        # Limitation: renaming a sparse field or changing the storing system is
        # currently not allowed
        if 'serialization_field_id' in vals or 'name' in vals:
            for field in self:
                if 'serialization_field_id' in vals and field.serialization_field_id.id != vals['serialization_field_id']:
                    raise UserError(_('Changing the storing system for field "%s" is not allowed.') % field.name)
                if field.serialization_field_id and (field.name != vals['name']):
                    raise UserError(_('Renaming sparse field "%s" is not allowed') % field.name)

        return super(IrModelFields, self).write(vals)

    def _reflect_model(self, model):
        super(IrModelFields, self)._reflect_model(model)

        # set 'serialization_field_id' on sparse fields; it is done here to
        # ensure that the serialized field is reflected already
        cr = self._cr
        query = """ UPDATE ir_model_fields
                    SET serialization_field_id=%s
                    WHERE model=%s AND name=%s
                    RETURNING id
                """
        fields_data = self._existing_field_data(model._name)

        for field in model._fields.values():
            ser_field_id = None
            ser_field_name = getattr(field, 'sparse', None)
            if ser_field_name:
                if ser_field_name not in fields_data:
                    msg = _("Serialization field `%s` not found for sparse field `%s`!")
                    raise UserError(msg % (ser_field_name, field.name))
                ser_field_id = fields_data[ser_field_name]['id']

            if fields_data[field.name]['serialization_field_id'] != ser_field_id:
                cr.execute(query, (ser_field_id, model._name, field.name))
                record = self.browse(cr.fetchone())
                self.pool.post_init(record.modified, ['serialization_field_id'])
                self.clear_caches()

    def _instanciate_attrs(self, field_data):
        attrs = super(IrModelFields, self)._instanciate_attrs(field_data)
        if field_data.get('serialization_field_id'):
            serialization_record = self.browse(field_data['serialization_field_id'])
            attrs['sparse'] = serialization_record.name
        return attrs


class TestSparse(models.TransientModel):
    _name = 'sparse_fields.test'
    _description = 'Sparse fields Test'

    data = fields.Serialized()
    boolean = fields.Boolean(sparse='data')
    integer = fields.Integer(sparse='data')
    float = fields.Float(sparse='data')
    char = fields.Char(sparse='data')
    selection = fields.Selection([('one', 'One'), ('two', 'Two')], sparse='data')
    partner = fields.Many2one('res.partner', sparse='data')
