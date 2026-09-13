# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class EventTag(models.Model):
    _name = 'event.tag'
    _inherit = ['event.tag', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'color']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['event.event'].tag_ids.ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['event.event']
