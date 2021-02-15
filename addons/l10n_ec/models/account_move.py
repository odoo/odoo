# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit='account.move'
    
    def _get_l10n_latam_documents_domain(self):
        #Filter document types according to ecuadorian move_type
        domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
        if self.country_code == 'EC':
            if self.move_type in ['out_invoice']:
                domain.extend([('l10n_ec_type', '=', 'out_invoice')])
            if self.move_type in ['out_refund']:
                domain.extend([('l10n_ec_type', '=', 'out_refund')])
            if self.move_type in ['in_invoice']:
                domain.extend([('l10n_ec_type', '=', 'in_invoice')])
            if self.move_type in ['in_refund']:
                domain.extend([('l10n_ec_type', '=', 'in_refund')])
        return domain
