# -*- coding: utf-8 -*-

from odoo import models, fields, api


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    ttype = fields.Selection(selection_add=[('serialized', 'serialized')])
    serialization_field_id = fields.Many2one('ir.model.fields', string='Serialization Field',
        ondelete='cascade', domain="[('ttype','=','serialized')]",
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

    def _reflect_field_params(self, field):
        params = super(IrModelFields, self)._reflect_field_params(field)

        params['serialization_field_id'] = None
        if getattr(field, 'sparse', None):
            model = self.env[field.model_name]
            serialization_field = model._fields.get(field.sparse)
            if serialization_field is None:
                raise UserError(_("Serialization field `%s` not found for sparse field `%s`!") % (field.sparse, field.name))
            serialization_record = self._reflect_field(serialization_field)
            params['serialization_field_id'] = serialization_record.id

        return params

    def _instanciate_attrs(self, field_data, partial):
        attrs = super(IrModelFields, self)._instanciate_attrs(field_data, partial)
        if field_data['serialization_field_id']:
            serialization_record = self.browse(field_data['serialization_field_id'])
            attrs['sparse'] = serialization_record.name
        return attrs


class TestSparse(models.TransientModel):
    _name = 'sparse_fields.test'

    data = fields.Serialized()
    boolean = fields.Boolean(sparse='data')
    integer = fields.Integer(sparse='data')
    float = fields.Float(sparse='data')
    char = fields.Char(sparse='data')
    selection = fields.Selection([('one', 'One'), ('two', 'Two')], sparse='data')
    partner = fields.Many2one('res.partner', sparse='data')
