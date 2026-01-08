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
        pass  # Deprecated since DnB

    def add_to_queue(self, partner_id):
        pass  # Deprecated since DnB
