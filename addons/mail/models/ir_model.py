# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import pycompat


class IrModel(models.Model):
    _inherit = 'ir.model'
    _order = 'is_mail_thread DESC, name ASC'

    is_mail_thread = fields.Boolean(
        string="Mail Thread", oldname='mail_thread', default=False,
        help="Whether this model supports messages and notifications.",
    )

    def unlink(self):
        # Delete followers for models that will be unlinked.
        query = "DELETE FROM mail_followers WHERE res_model IN %s"
        self.env.cr.execute(query, [tuple(self.mapped('model'))])
        return super(IrModel, self).unlink()

    @api.multi
    def write(self, vals):
        if self and 'is_mail_thread' in vals:
            if not all(rec.state == 'manual' for rec in self):
                raise UserError(_('Only custom models can be modified.'))
            if not all(rec.is_mail_thread <= vals['is_mail_thread'] for rec in self):
                raise UserError(_('Field "Mail Thread" cannot be changed to "False".'))
            res = super(IrModel, self).write(vals)
            # setup models; this reloads custom models in registry
            self.pool.setup_models(self._cr)
            # update database schema of models
            models = self.pool.descendants(self.mapped('model'), '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))
        else:
            res = super(IrModel, self).write(vals)
        return res

    def _reflect_model_params(self, model):
        vals = super(IrModel, self)._reflect_model_params(model)
        vals['is_mail_thread'] = issubclass(type(model), self.pool['mail.thread'])
        return vals

    @api.model
    def _instanciate(self, model_data):
        model_class = super(IrModel, self)._instanciate(model_data)
        if model_data.get('is_mail_thread') and model_class._name != 'mail.thread':
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, pycompat.string_types) else parents
            model_class._inherit = parents + ['mail.thread']
        return model_class


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    track_visibility = fields.Selection(
        [('onchange', "On Change"), ('always', "Always")], string="Tracking",
        help="When set, every modification to this field will be tracked in the chatter.",
    )

    def _reflect_field_params(self, field):
        vals = super(IrModelField, self)._reflect_field_params(field)
        vals['track_visibility'] = getattr(field, 'track_visibility', None)
        return vals

    def _instanciate_attrs(self, field_data):
        attrs = super(IrModelField, self)._instanciate_attrs(field_data)
        if attrs and field_data.get('track_visibility'):
            attrs['track_visibility'] = field_data['track_visibility']
        return attrs
