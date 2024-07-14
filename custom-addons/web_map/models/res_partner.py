# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    contact_address_complete = fields.Char(compute='_compute_complete_address', store=True)

    @api.model
    def update_latitude_longitude(self, partners):
        partners_data = defaultdict(list)

        for partner in partners:
            if 'id' in partner and 'partner_latitude' in partner and 'partner_longitude' in partner:
                partners_data[(partner['partner_latitude'], partner['partner_longitude'])].append(partner['id'])

        for values, partner_ids in partners_data.items():
            # NOTE this should be done in sudo to avoid crashing as soon as the view is used
            self.browse(partner_ids).sudo().write({
                'partner_latitude': values[0],
                'partner_longitude': values[1],
            })

        return {}

    @api.onchange('street', 'zip', 'city', 'state_id', 'country_id')
    def _delete_coordinates(self):
        self.partner_latitude = False
        self.partner_longitude = False

    @api.depends('street', 'zip', 'city', 'country_id')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ''
            if record.street:
                record.contact_address_complete += record.street + ', '
            if record.zip:
                record.contact_address_complete += record.zip + ' '
            if record.city:
                record.contact_address_complete += record.city + ', '
            if record.state_id:
                record.contact_address_complete += record.state_id.name + ', '
            if record.country_id:
                record.contact_address_complete += record.country_id.name
            record.contact_address_complete = record.contact_address_complete.strip().strip(',')
