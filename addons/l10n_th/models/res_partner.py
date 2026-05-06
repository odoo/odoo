# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_branch_name = fields.Char(compute="_compute_l10n_th_branch_name")
    l10n_th_title = fields.Selection([
        ("khun", "Khun"),
        ("mr", "Mr."),
        ("ms", "Ms."),
        ("mrs", "Mrs.")],
        string="Title",
    )
    l10n_th_company_type = fields.Selection([
        ("company_ltd", "Company Limited"),
        ("pub_company_ltd", "Public Company Limited"),
        ("ltd_partner", "Limited Partnership"),
        ("foundation", "Foundation"),
        ("asso", "Association"),
        ("joint_venture", "Joint Venture"),
        ("others", "Others")],
        string="Company Type",
    )

    def _compute_is_company(self):
        super()._compute_is_company()
        self.filtered(
            lambda p: p.country_code == 'TH' and not (p.vat or '').startswith("0"),
        ).is_company = False

    @api.depends('additional_identifiers')
    def _compute_l10n_th_branch_name(self):
        for partner in self:
            if not partner.is_company or partner.country_code != 'TH':
                partner.l10n_th_branch_name = ""
            else:
                code = partner._get_additional_identifier('TH_BRANCH_CODE')
                partner.l10n_th_branch_name = partner.env._("Branch %(code)s", code=code) if code and code != "00000" else partner.env._(
                    "Headquarter")
