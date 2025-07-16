# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _load_pos_self_data_fields(self, config):
        return super()._load_pos_self_data_fields(config) + ['image_1024']

    def _can_return_content(self, field_name=None, access_token=None):
        if (
            field_name in ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
            and self.sudo().event_ticket_ids
        ):
            return True
        return super()._can_return_content(field_name, access_token)
