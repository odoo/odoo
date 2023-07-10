# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ResPartnerAutocompleteSync(models.Model):
    _name = 'res.partner.autocomplete.sync'
    _description = 'Partner Autocomplete Sync'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade')
    synched = fields.Boolean('Is synched', default=False)

    @api.model
    def start_sync(self):
        to_sync_items = self.search([('synched', '=', False)])
        for to_sync_item in to_sync_items:
            partner = to_sync_item.partner_id

            params = {
                'partner_gid': partner.partner_gid,
            }

            if partner.vat and partner._is_vat_syncable(partner.vat):
                params['vat'] = partner.vat
                _, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('update', params)
                if error:
                    _logger.warning('Send Partner to sync failed: %s', str(error))

            to_sync_item.write({'synched': True})

    def add_to_queue(self, partner_id):
        to_sync = self.search([('partner_id', '=', partner_id)])
        if not to_sync:
            to_sync = self.create({'partner_id': partner_id})
        return to_sync
