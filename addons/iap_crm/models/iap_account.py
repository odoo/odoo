# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class IapAccount(models.Model):
    _inherit = 'iap.account'

    def _get_brand_name_from_service_name(self, service_name):
        if service_name == 'lead_mining_request':
            return _('Lead Generation')
        if service_name == 'lead_enrichment_email':
            return _('Lead Enrichment')
        if service_name == 'reveal':
            return _('Reveal')
        return super(IapAccount, self)._get_brand_name_from_service_name(service_name)
