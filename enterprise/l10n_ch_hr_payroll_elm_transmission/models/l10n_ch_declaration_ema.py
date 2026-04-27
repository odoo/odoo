# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import api, fields, models, _
from ..api.swissdec_declarations import SwissdecDeclaration
from odoo.tools.misc import format_date


class L10nChEMADeclaration(models.Model):
    _name = 'l10n.ch.ema.declaration'
    _inherit = 'l10n.ch.swissdec.transmitter'
    _description = 'Entry / Withdrawal / Mutation Declaration for AVS / CAF / LPP'
    _order = "month desc, year desc"


    avs_institution_ids = fields.Many2many('l10n.ch.social.insurance')
    caf_institution_ids = fields.Many2many('l10n.ch.compensation.fund')
    lpp_institution_ids = fields.Many2many('l10n.ch.lpp.insurance')


    def action_prepare_data(self):
        self.ensure_one()
        super().action_prepare_data()
        declaration, institutions = self.env["l10n.ch.employee.yearly.values"]._get_monthly_ema(year=self.year, month=int(self.month), company_id=self.company_id)
        self.l10n_ch_declare_salary_data = declaration
        self.avs_institution_ids = self.env['l10n.ch.social.insurance'].browse(institutions.get("AVS", []))
        self.caf_institution_ids = self.env['l10n.ch.compensation.fund'].browse(institutions.get("CAF", []))
        self.lpp_institution_ids = self.env['l10n.ch.lpp.insurance'].browse(institutions.get("LPP", []))

    def _get_institutions(self):
        return list(self.avs_institution_ids) + list(self.caf_institution_ids) + list(self.lpp_institution_ids)

    def _get_declaration(self):
        self.ensure_one()
        swissdec_declaration = SwissdecDeclaration()
        return swissdec_declaration.create_declare_salary(
            institutions_to_process=self._get_institutions(),
            company_id=self.company_id,
            staff=self.l10n_ch_declare_salary_data,
            declaration_year=self.year,
            test_case=self.test_transmission,
            substitution_declaration_id=self.substituted_declaration_id.swissdec_declaration_id,
            general_validasof=format_date(self.env, datetime.date(self.year, int(self.month), 1), date_format='yyyy-MM-dd')
        )
