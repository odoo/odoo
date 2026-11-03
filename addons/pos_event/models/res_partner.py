# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        events = self.env['event.event'].search([
            ('event_ticket_ids.product_id', '!=', False),
        ])
        venue_ids = events.address_id.ids
        if venue_ids:
            domain = Domain.OR([domain, [('id', 'in', venue_ids)]])
        return domain
