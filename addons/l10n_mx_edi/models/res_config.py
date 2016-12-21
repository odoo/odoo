# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    l10n_mx_edi_cer = fields.Binary(
        related='company_id.l10n_mx_edi_cer',
        string='MX Certificate*')
    l10n_mx_edi_cer_key = fields.Binary(
        related='company_id.l10n_mx_edi_cer_key',
        string='MX Certificate Key*')
    l10n_mx_edi_cer_password = fields.Char(
        related='company_id.l10n_mx_edi_cer_password',
        string='MX Certificate Password*')
    l10n_mx_edi_pac = fields.Selection(
        related='company_id.l10n_mx_edi_pac',
        string='MX PAC*')
    l10n_mx_edi_pac_test_env = fields.Boolean(
        related='company_id.l10n_mx_edi_pac_test_env',
        string='MX PAC test environment*')
    l10n_mx_edi_pac_username = fields.Char(
        related='company_id.l10n_mx_edi_pac_username',
        string='MX PAC username*')
    l10n_mx_edi_pac_password = fields.Char(
        related='company_id.l10n_mx_edi_pac_password',
        string='MX PAC password*')