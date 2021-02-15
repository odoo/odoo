# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    _ACCOUNT_TYPE = [
        ('savings', 'Savings Account'),  
        ('checking', 'Checking Account'),
        ]
    
    l10n_ec_account_type = fields.Selection(
        _ACCOUNT_TYPE,
        string='Type',
        default='checking',
        help='Select here the type of account (savings or checking)'
        )
    
    @api.model
    def _get_supported_account_types(self):
        rslt = super(ResPartnerBank, self)._get_supported_account_types()
        rslt.append(('savings', _('Savings Account')))
        rslt.append(('checking', _('Checking Account')))
        return rslt
    
    @api.depends('acc_number')
    def _compute_acc_type(self):
        for bank in self:
            if bank.company_id.country_code == 'EC':
                bank.acc_type = bank.l10n_ec_account_type
            else:
                super(ResPartnerBank, self)._compute_acc_type()
    
