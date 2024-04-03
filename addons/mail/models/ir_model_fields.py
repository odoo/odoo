# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    tracking = fields.Integer(
        string="Enable Ordered Tracking",
        help="If set every modification done to this field is tracked in the chatter. Value is used to order tracking values.",
    )

    def _reflect_field_params(self, field, model_id):
        """ Tracking value can be either a boolean enabling tracking mechanism
        on field, either an integer giving the sequence. Default sequence is
        set to 100. """
        vals = super(IrModelField, self)._reflect_field_params(field, model_id)
        tracking = getattr(field, 'tracking', None)
        if tracking is True:
            tracking = 100
        elif tracking is False:
            tracking = None
        vals['tracking'] = tracking
        return vals

    def _instanciate_attrs(self, field_data):
        attrs = super(IrModelField, self)._instanciate_attrs(field_data)
        if attrs and field_data.get('tracking'):
            attrs['tracking'] = field_data['tracking']
        return attrs
