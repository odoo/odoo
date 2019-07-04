# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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

    def unlink(self):
        """
        Delete 'mail.tracking.value's when a module is uninstalled
        """
        if self:
            query = """
                DELETE FROM mail_tracking_value
                WHERE id IN (
                    SELECT t.id
                    FROM mail_tracking_value t
                    INNER JOIN mail_message m ON (m.id = t.mail_message_id)
                    INNER JOIN ir_model_fields f ON (t.field = f.name AND m.model = f.model)
                    WHERE f.id IN %s
                );
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            # DLE P116: test_unlinked_field
            for values in self.env.all.towrite[self.model].values():
                if self.name in values:
                    del values[self.name]
        return super(IrModelField, self).unlink()
