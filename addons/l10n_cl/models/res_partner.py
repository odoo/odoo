# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _sii_taxpayer_types = [
        ('1', _('VAT Affected (1st Category)')),
        ('2', _('Fees Receipt Issuer (2nd category)')),
        ('3', _('End Consumer')),
        ('4', _('Foreigner')),
    ]

    l10n_cl_sii_taxpayer_type = fields.Selection(
        _sii_taxpayer_types, 'Taxpayer Type', index=True,
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')
