# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ec_edi_certificate = fields.Binary(string='Certificate', related="company_id.l10n_ec_edi_certificate", readonly=False)
    l10n_ec_edi_cert_name = fields.Char(string='dummy', related="company_id.l10n_ec_edi_cert_name", readonly=False)
    l10n_ec_edi_password = fields.Char(string='Password', related="company_id.l10n_ec_edi_password", readonly=False)
    l10n_ec_edi_env = fields.Selection(related="company_id.l10n_ec_edi_env", readonly=False)