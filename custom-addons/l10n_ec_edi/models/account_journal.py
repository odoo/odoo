# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_ec_withhold_type = fields.Selection(
        selection=[
            ('out_withhold', "Sales Withhold"),
            ('in_withhold', "Purchase Withhold")],
        string="Withhold Type",
        help="Ecuador: Select if you want to use this Journal to create Purchase or Sales withholdings.",
    )
    l10n_ec_is_purchase_liquidation = fields.Boolean(
        string="Purchase Liquidations",
        help="Ecuador: Check if this journal is dedicated to purchase liquidations")

    @api.depends('l10n_ec_withhold_type', 'l10n_ec_is_purchase_liquidation', 'l10n_latam_use_documents')
    def _compute_edi_format_ids(self):
        # EXTENDS account, add onchange dependencies to fields used by '_is_compatible_with_journal()'
        super()._compute_edi_format_ids()

    @api.depends('l10n_ec_withhold_type', 'l10n_ec_is_purchase_liquidation')
    def _compute_compatible_edi_ids(self):
        # EXTENDS account, add onchange dependencies to fields used by '_is_compatible_with_journal()'
        super()._compute_compatible_edi_ids()

    @api.onchange('type', 'l10n_ec_withhold_type')
    def _onchange_withhold_type(self):
        # forcefully clear the field as the field becomes invisible
        if self.type != 'general':
            self.l10n_ec_withhold_type = False

    @api.onchange('type')
    def _onchange_type_is_purchase_liquidation(self):
        # forcefully clear the field as the field
        if self.type != 'purchase':
            self.l10n_ec_is_purchase_liquidation = False

    @api.depends('type', 'l10n_latam_use_documents', 'l10n_ec_withhold_type', 'l10n_ec_is_purchase_liquidation')
    def _compute_l10n_ec_require_emission(self):
        # EXTENDS l10n_ec, sets required emission also for withholds and purchase liquidations
        super()._compute_l10n_ec_require_emission()
        for journal in self.filtered(lambda j: j.country_code == 'EC'):
            if journal.l10n_ec_is_purchase_liquidation or journal.l10n_ec_withhold_type == 'in_withhold':
                journal.l10n_ec_require_emission = True

    @api.constrains('l10n_ec_entity', 'l10n_ec_emission', 'type', 'l10n_ec_withhold_type', 'l10n_ec_is_purchase_liquidation')
    def _l10n_ec_check_duplicated_entity_emission(self):
        for journal in self:
            if not journal.country_code == 'EC' or not journal.l10n_ec_entity or not journal.l10n_ec_emission:
                continue
            duplicated_journals = self.search([
                *self._check_company_domain(journal.company_id),
                ('id', '!=', journal.id),  # other journals
                ('type', '=', journal.type),
                ('l10n_ec_withhold_type', '=', journal.l10n_ec_withhold_type),
                ('l10n_ec_is_purchase_liquidation', '=', journal.l10n_ec_is_purchase_liquidation),
                ('l10n_ec_entity', '=', journal.l10n_ec_entity),
                ('l10n_ec_emission', '=', journal.l10n_ec_emission),
            ])
            if duplicated_journals:
                raise ValidationError(_("Duplicated journal (entity, emission) pair. You probably encoded twice the same journal:\n%s", '\n'.join(
                    '%(l10n_ec_entity)s-%(l10n_ec_emission)s' % j for j in duplicated_journals
                )))
