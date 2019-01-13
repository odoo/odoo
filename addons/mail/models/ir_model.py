# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IrModel(models.Model):
    _inherit = 'ir.model'
    _order = 'is_mail_thread DESC, name ASC'

    is_mail_thread = fields.Boolean(
        string="Mail Thread", oldname='mail_thread', default=False,
        help="Whether this model supports messages and notifications.",
    )
    is_mail_activity = fields.Boolean(
        string="Mail Activity", default=False,
        help="Whether this model supports activities.",
    )

    def unlink(self):
        # Delete followers for models that will be unlinked.
        query = "DELETE FROM mail_followers WHERE res_model IN %s"
        self.env.cr.execute(query, [tuple(self.mapped('model'))])
        return super(IrModel, self).unlink()

    @api.multi
    def write(self, vals):
        if self and ('is_mail_thread' in vals or 'is_mail_activity' in vals):
            if not all(rec.state == 'manual' for rec in self):
                raise UserError(_('Only custom models can be modified.'))
            if 'is_mail_thread' in vals and not all(rec.is_mail_thread <= vals['is_mail_thread'] for rec in self):
                raise UserError(_('Field "Mail Thread" cannot be changed to "False".'))
            if 'is_mail_activity' in vals and not all(rec.is_mail_activity <= vals['is_mail_activity'] for rec in self):
                raise UserError(_('Field "Mail Activity" cannot be changed to "False".'))
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
        vals['is_mail_activity'] = issubclass(type(model), self.pool['mail.activity.mixin'])
        return vals

    @api.model
    def _instanciate(self, model_data):
        model_class = super(IrModel, self)._instanciate(model_data)
        if model_data.get('is_mail_thread') and model_class._name != 'mail.thread':
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, str) else parents
            model_class._inherit = parents + ['mail.thread']
        if model_data.get('is_mail_activity') and model_class._name != 'mail.activity.mixin':
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, str) else parents
            model_class._inherit = parents + ['mail.activity.mixin']
        return model_class


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    tracking = fields.Integer(
        string="Enable Ordered Tracking",
        help="If set every modification done to this field is tracked in the chatter. Value is used to order tracking values.",
    )

    def _reflect_field_params(self, field):
        """ Tracking value can be either a boolean enabling tracking mechanism
        on field, either an integer giving the sequence. Default sequence is
        set to 100. """
        vals = super(IrModelField, self)._reflect_field_params(field)
        tracking = getattr(field, 'tracking', None)
        if tracking is True:
            tracking = 100
        elif tracking is False:
            tracking = None
        vals['tracking'] = tracking
        return vals

    def _instanciate_attrs(self, field_data):
        attrs = super(IrModelField, self)._instanciate_attrs(field_data)
        if field_data.get('tracking'):
            attrs['tracking'] = field_data['tracking']
        return attrs
