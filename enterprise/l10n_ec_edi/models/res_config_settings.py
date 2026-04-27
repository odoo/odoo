# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ec_legal_name = fields.Char(
        related='company_id.l10n_ec_legal_name',
        readonly=False,
    )
    l10n_ec_production_env = fields.Boolean(
        related='company_id.l10n_ec_production_env',
        readonly=False,
    )
    l10n_ec_edi_certificate_id = fields.Many2one(
        related='company_id.l10n_ec_edi_certificate_id',
        readonly=False,
    )
    l10n_ec_forced_accounting = fields.Boolean(
        related='company_id.l10n_ec_forced_accounting',
        readonly=False,
    )
    l10n_ec_special_taxpayer_number = fields.Char(
        related='company_id.l10n_ec_special_taxpayer_number',
        readonly=False,
    )
    l10n_ec_withhold_agent_number = fields.Char(
        related='company_id.l10n_ec_withhold_agent_number',
        readonly=False,
        help='Last 8 digits',
    )
    l10n_ec_regime = fields.Selection(
        related='company_id.l10n_ec_regime',
        readonly=False,
    )
    l10n_ec_withhold_goods_tax_id = fields.Many2one(
        related='company_id.l10n_ec_withhold_goods_tax_id',
        readonly=False,
    )
    l10n_ec_withhold_services_tax_id = fields.Many2one(
        related='company_id.l10n_ec_withhold_services_tax_id',
        readonly=False,
    )
    l10n_ec_withhold_credit_card_tax_id = fields.Many2one(
        related='company_id.l10n_ec_withhold_credit_card_tax_id',
        readonly=False,
    )
    l10n_ec_tax_base_sale_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ec_tax_base_sale_account_id',
        readonly=False,
        domain=[('deprecated', '=', False)],
        string="Sales Tax Base Account",
    )
    l10n_ec_tax_base_purchase_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ec_tax_base_purchase_account_id',
        readonly=False,
        domain=[('deprecated', '=', False)],
        string="Purchase Tax Base Account",
    )
