# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_edi_provider = fields.Selection(
        string="Signature Provider",
        readonly=False,
        related="company_id.l10n_pe_edi_provider",
        help="""
        Selector for the service we are going to use to report the invoices:\n
        - IAP: This is an odoo service that will send the unsigned documents to a PSE and process their response.\n
        - Estela (formerly DIGIFLOW): With the certified that digiflow provide you, user and password you will report the invoices to them.\n
        - SUNAT: You will report the invoices directly to them using your own certified, user and password.\n
        """)
    l10n_pe_edi_test_env = fields.Boolean(
        string="Testing Environment",
        related='company_id.l10n_pe_edi_test_env',
        readonly=False)
    l10n_pe_edi_provider_username = fields.Char(
        string="SOL User",
        related="company_id.l10n_pe_edi_provider_username",
        readonly=False,
        help="SUNAT Operaciones en Línea")
    l10n_pe_edi_provider_password = fields.Char(
        string="SOL Password",
        related="company_id.l10n_pe_edi_provider_password",
        readonly=False,
        help="SUNAT Operaciones en Línea")
    l10n_pe_edi_certificate_id = fields.Many2one(
        related="company_id.l10n_pe_edi_certificate_id",
        readonly=False,
        domain="[('company_id', '=', company_id), ('is_valid', '=', True)]")
