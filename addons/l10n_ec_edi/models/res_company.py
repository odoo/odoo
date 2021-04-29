# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'
    
    l10n_ec_edi_certificate = fields.Binary(string='Certificate')
    l10n_ec_edi_cert_name = fields.Char(string='dummy')
    l10n_ec_edi_password = fields.Char(string='Password')
    l10n_ec_edi_env = fields.Selection([
        ('1', 'Test'),
        ('2', 'Production')
    ], string='Environment', default='1')


