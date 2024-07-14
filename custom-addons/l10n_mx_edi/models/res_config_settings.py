# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_mx_edi_pac = fields.Selection(related='company_id.l10n_mx_edi_pac', readonly=False)
    l10n_mx_edi_pac_test_env = fields.Boolean(related='company_id.l10n_mx_edi_pac_test_env', readonly=False)
    l10n_mx_edi_pac_username = fields.Char(related='company_id.l10n_mx_edi_pac_username', readonly=False)
    l10n_mx_edi_pac_password = fields.Char(related='company_id.l10n_mx_edi_pac_password', readonly=False)
    l10n_mx_edi_certificate_ids = fields.One2many(related='company_id.l10n_mx_edi_certificate_ids', readonly=False)
    l10n_mx_edi_fiscal_regime = fields.Selection(related='company_id.l10n_mx_edi_fiscal_regime', readonly=False)
