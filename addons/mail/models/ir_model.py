# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IrModel(models.Model):
    _inherit = 'ir.model'
    _order = 'is_mail_thread DESC, model ASC'

    is_mail_thread = fields.Boolean(
        string="Mail Thread", oldname='mail_thread',
        compute='_compute_is_mail_thread', inverse='_inverse_is_mail_thread', store=True,
        help="Whether this model supports messages and notifications.",
    )

    @api.depends('model')
    def _compute_is_mail_thread(self):
        MailThread = self.pool['mail.thread']
        for rec in self:
            if rec.model != 'mail.thread':
                Model = self.pool.get(rec.model)
                rec.is_mail_thread = Model and issubclass(Model, MailThread)

    def _inverse_is_mail_thread(self):
        pass        # do nothing; this enables to set the value of the field

    @api.multi
    def write(self, vals):
        res = super(IrModel, self).write(vals)
        if self and 'is_mail_thread' in vals:
            if not all(rec.state == 'manual' for rec in self):
                raise UserError(_('Only custom models can be modified.'))
            # one can only change is_mail_thread from False to True
            if not all(rec.is_mail_thread <= vals['is_mail_thread'] for rec in self):
                raise UserError(_('Field "Mail Thread" cannot be changed to "False".'))
            # setup models; this reloads custom models in registry
            self.pool.setup_models(self._cr, partial=(not self.pool.ready))
            # update database schema of models
            models = self.pool.descendants(self.mapped('model'), '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))
            self.pool.signal_registry_change()
        return res

    @api.model
    def _instanciate(self, model_data):
        model_class = super(IrModel, self)._instanciate(model_data)
        if model_data.get('is_mail_thread'):
            parents = model_class._inherit or []
            parents = [parents] if isinstance(parents, basestring) else parents
            model_class._inherit = parents + ['mail.thread']
        return model_class


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    track_visibility = fields.Selection(
        [('onchange', "On Change"), ('always', "Always")], string="Tracking",
        compute='_compute_track_visibility', inverse='_inverse_track_visibility', store=True,
        help="When set, every modification to this field will be tracked in the chatter.",
    )

    @api.depends('name')
    def _compute_track_visibility(self):
        for rec in self:
            if rec.model in self.env:
                field = self.env[rec.model]._fields.get(rec.name)
                rec.track_visibility = getattr(field, 'track_visibility', False)

    def _inverse_track_visibility(self):
        pass        # do nothing; this enables to set the value of the field

    def _instanciate_attrs(self, field_data, partial):
        attrs = super(IrModelField, self)._instanciate_attrs(field_data, partial)
        if field_data.get('track_visibility'):
            attrs['track_visibility'] = field_data['track_visibility']
        return attrs
