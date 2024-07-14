# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ec_legal_name = fields.Char(string="Company legal name")
    l10n_ec_production_env = fields.Boolean(
        string="Use production servers",
        default=False,
    )
    l10n_ec_edi_certificate_id = fields.Many2one(
        string="Certificate file for SRI",
        comodel_name='l10n_ec_edi.certificate',
        groups='base.group_system',
    )
    l10n_ec_special_taxpayer_number = fields.Char(
        string="Special Taxpayer Number",
        help="If set, your company is considered a Special Taxpayer, this number will be printed in electronic invoices and reports",
    )
    l10n_ec_withhold_agent_number = fields.Char(
        string="Withhold Agent Number",
        help="Last digits from the SRI resolution number in which your company became a designated withholder agent. "
        "If the resolution number where NAC-DNCRASC20-00000001 then the number should be 1",
    )
    l10n_ec_forced_accounting = fields.Boolean(
        string="Forced to Keep Accounting Books",
        default=True,
        help="Check if you are obligated to keep accounting books, will be used for printing electronic invoices and reports",
    )
    l10n_ec_regime = fields.Selection( # We do a selection as there is a good chance a new regime will be put in place
        selection=[
            ('regular', "Regular Regime (without additional messages in the RIDE)"),
            ('rimpe', "RIMPE Regime"),
        ],
        string="Regime",
        default='regular',
        required=True,
        help="Will show an additional label on the RIDE and XML called 'CONTRIBUYENTE REGIMEN RIMPE', "
        "select it if your company is in the SRI Excel registry, "
        "It doesn't affect the computation of withholds. "
    )
    l10n_ec_withhold_goods_tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        string="Withhold Consumables",
        help="When no profit withhold is found in partner or product, if product is a stockable or consumable"
             "the withhold fallbacks to this tax code"
    )
    l10n_ec_withhold_services_tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        string="Withhold Services",
        help="When no profit withhold is found in partner or product, if product is a service or not set'"
             "the withhold fallbacks to this tax code"
    )
    l10n_ec_withhold_credit_card_tax_id = fields.Many2one(
        comodel_name='account.tax',
        check_company=True,
        string="Withhold Credit Card",
        help="When payment method will be credit card apply this withhold",
    )

    def _l10n_ec_is_demo_environment(self):
        return not self.l10n_ec_production_env and not self.sudo().l10n_ec_edi_certificate_id

    def _l10n_ec_set_taxpayer_type_for_demo(self):
        """Used for EC demo company to configure the default withhold taxes on common taxpayer types."""
        type01 = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_01').with_company(self)
        type01.profit_withhold_tax_id = self.env.ref(f'account.{self.id}_tax_withhold_profit_303')
        type01.vat_goods_withhold_tax_id = self.env.ref(f'account.{self.id}_tax_withhold_vat_10')
        type01.vat_services_withhold_tax_id = self.env.ref(f'account.{self.id}_tax_withhold_vat_20')

        type06 = self.env.ref('l10n_ec_edi.l10n_ec_taxpayer_type_06').with_company(self)
        type06.profit_withhold_tax_id = self.env.ref(f'account.{self.id}_tax_withhold_profit_303')
