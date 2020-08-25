# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class AccountMove(models.Model):
    _inherit='account.move'


    def _get_l10n_latam_documents_domain(self):
        '''
        Invocamos el metodo _get_l10n_latam_documents_domain para filtrar los tipos de documentos
        '''
        domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
        if self.l10n_latam_country_code == 'EC':
            if self.type in ['out_invoice']:
                domain.extend([('l10n_ec_type', '=', 'out_invoice')])
            if self.type in ['out_refund']:
                domain.extend([('l10n_ec_type', '=', 'out_refund')])
            if self.type in ['in_invoice']:
                domain.extend([('l10n_ec_type', '=', 'in_invoice')])
            if self.type in ['in_refund']:
                domain.extend([('l10n_ec_type', '=', 'in_refund')])
        return domain
    
