# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    contact_address_complete = fields.Char(compute='_compute_complete_address', store=True)

    def write(self, vals):
        # Reset latitude/longitude in case we modify the address without
        # updating the related geolocation fields
        if any(field in vals for field in ['street', 'zip', 'city', 'state_id', 'country_id']) \
            and not all('partner_%s' % field in vals for field in ['latitude', 'longitude']):
            vals.update({
                'partner_latitude': False,
                'partner_longitude': False,
            })
        return super().write(vals)

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['partner_latitude', 'partner_longitude']

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        result = super()._formatting_address_fields()
        return [item for item in result if item not in ['partner_latitude', 'partner_longitude']]

    @api.model
    def update_latitude_longitude(self, partners):
        partners_data = defaultdict(list)

        for partner in partners:
            if 'id' in partner and 'partner_latitude' in partner and 'partner_longitude' in partner:
                partners_data[(partner['partner_latitude'], partner['partner_longitude'])].append(partner['id'])

        for values, partner_ids in partners_data.items():
            if self.env.user.has_group('base.group_user'):
                partners = self.browse(partner_ids).sudo()
            else:
                partners = self.browse(partner_ids)
            # NOTE this should be done in sudo if internal user to avoid crashing as soon as the view is used
            partners.write({
                'partner_latitude': values[0],
                'partner_longitude': values[1],
            })

        return {}

    @api.onchange('street', 'zip', 'city', 'state_id', 'country_id')
    def _delete_coordinates(self):
        self.partner_latitude = False
        self.partner_longitude = False

    @api.depends('street', 'street2', 'zip', 'city', 'country_id')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ''
            if record.street:
                record.contact_address_complete += record.street + ', '
            if record.street2:
                record.contact_address_complete += record.street2 + ', '
            if record.zip:
                record.contact_address_complete += record.zip + ' '
            if record.city:
                record.contact_address_complete += record.city + ', '
            if record.state_id:
                record.contact_address_complete += record.state_id.name + ', '
            if record.country_id:
                record.contact_address_complete += record.country_id.name
            record.contact_address_complete = record.contact_address_complete.strip().strip(',')
