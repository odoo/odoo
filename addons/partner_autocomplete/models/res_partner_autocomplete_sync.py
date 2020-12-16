# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ResPartnerAutocompleteSync(models.Model):
    _name = 'res.partner.autocomplete.sync'
    _description = 'Partner Autocomplete Sync'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete='cascade', required=True)
    synched = fields.Boolean('Is synched', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        syncs = super().create(vals_list)
        syncs and syncs._update_cron()
        return syncs

    def write(self, values):
        res = super().write(values)
        if 'state' in values:
            self and self._update_cron()
        return res

    def unlink(self):
        res = super().unlink()
        self and self._update_cron()
        return res

    @api.model
    def _update_cron(self):
        cron = self.env.ref('partner_autocomplete.ir_cron_partner_autocomplete', raise_if_not_found=False)
        cron and cron.toggle(
            model=self._name,
            domain=[],
        )

    @api.model
    def _start_sync(self):
        to_sync_items = self.search([('synched', '=', False)])
        for to_sync_item in to_sync_items:
            partner = to_sync_item.partner_id

            if partner.vat and partner._is_vat_syncable(partner.vat):
                params = {
                    'partner_gid': partner.partner_gid,
                    'vat': partner.vat,
                }
                result, error = partner._rpc_remote_api('update', params)
                if error:
                    _logger.error('Send Partner to sync failed: %s' % str(error))

            to_sync_item.write({'synched': True})

    def add_to_queue(self, partner_id):
        to_sync = self.search([('partner_id', '=', partner_id)])
        if not to_sync:
            to_sync = self.create({'partner_id': partner_id})
        return to_sync
