# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import groupby


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.ondelete(at_uninstall=False)
    def _unlink_tracking(self):
        """ When unlinking fields populate tracking value table with relevant
        information. That way if a field is removed (custom tracked, migration
        or any other reason) we keep the tracking and its relevant information.
        Do it only when unlinking fields so that we don't duplicate field
        information for most tracking. """
        tracked = self.filtered('tracking')
        if tracked:
            tracking_values = self.env['mail.tracking.value'].search(
                [('field_id', 'in', tracked.ids)]
            )
            field_to_trackings = groupby(tracking_values, lambda track: track.field_id)
            for field, trackings in field_to_trackings:
                if field.model_id.model not in self.env:
                    # Model is already deleted
                    continue
                self.env['mail.tracking.value'].concat(trackings).write({
                    'field_info': {
                        'desc': field.field_description,
                        'name': field.name,
                        'sequence': self.env[field.model_id.model]._mail_track_get_field_sequence(field.name),
                        'type': field.ttype,
                    }
                })
