# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    _transaction_code_domain = '''
        [('type', '=', 'transaction'),
        '|', ('expiry_date', '>', context_today().strftime('%Y-%m-%d')), ('expiry_date', '=', None),
        '|', ('start_date', '<', context_today().strftime('%Y-%m-%d')), ('start_date', '=', None)]
    '''

    intrastat_region_id = fields.Many2one('account.intrastat.code', string='Intrastat region',
        domain="[('type', '=', 'region'), '|', ('country_id', '=', None), ('country_id', '=', country_id)]")
    intrastat_transport_mode_id = fields.Many2one('account.intrastat.code', string='Default transport mode',
        domain="[('type', '=', 'transport')]")
    intrastat_default_invoice_transaction_code_id = fields.Many2one('account.intrastat.code',
        string='Default invoice transaction code', domain=_transaction_code_domain)
    intrastat_default_refund_transaction_code_id = fields.Many2one('account.intrastat.code',
        string='Default refund transaction code', domain=_transaction_code_domain)
