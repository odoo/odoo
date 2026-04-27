# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_cl_dte_email = fields.Char('DTE Email', related='company_id.l10n_cl_dte_email', readonly=False)
    l10n_cl_dte_service_provider = fields.Selection(related='company_id.l10n_cl_dte_service_provider', readonly=False,
        help='Please select your company service provider for DTE service.')
    l10n_cl_dte_resolution_number = fields.Char(
        'SII Exempt Resolution Number',
        related='company_id.l10n_cl_dte_resolution_number', readonly=False,
        help='This value must be provided and must appear in your pdf or printed tribute document, under the '
             'electronic stamp to be legally valid.')
    l10n_cl_dte_resolution_date = fields.Date(
        'SII Exempt Resolution Date', related='company_id.l10n_cl_dte_resolution_date', readonly=False)
    l10n_cl_sii_regional_office = fields.Selection(related='company_id.l10n_cl_sii_regional_office', readonly=False,
        translate=False, string='SII Regional Office')
    l10n_cl_activity_description = fields.Char(
        string='Glosa Giro', related='company_id.l10n_cl_activity_description', readonly=False)
    l10n_cl_company_activity_ids = fields.Many2many('l10n_cl.company.activities', string='Activities Names',
        related='company_id.l10n_cl_company_activity_ids', readonly=False,
        help='Please select the SII registered economic activities codes for the company')
    l10n_cl_sii_taxpayer_type = fields.Selection(related='company_id.l10n_cl_sii_taxpayer_type', readonly=False,
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')
    l10n_cl_is_there_shared_certificate = fields.Boolean(related='company_id.l10n_cl_is_there_shared_certificate')
