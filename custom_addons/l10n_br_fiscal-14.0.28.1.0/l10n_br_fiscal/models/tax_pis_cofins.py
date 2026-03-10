# Copyright (C) 2019  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models

from .. import tools
from ..constants.fiscal import (
    TAX_DOMAIN_COFINS,
    TAX_DOMAIN_COFINS_ST,
    TAX_DOMAIN_PIS,
    TAX_DOMAIN_PIS_ST,
)


class TaxPisCofins(models.Model):
    _name = "l10n_br_fiscal.tax.pis.cofins"
    _description = "Tax PIS/COFINS"

    code = fields.Char(required=True)

    name = fields.Text(required=True, index=True)

    piscofins_type = fields.Selection(
        selection=[
            ("ncm", _("NCM")),
            ("product", _("Product")),
            ("company", _("Company")),
        ],
        default="ncm",
        string="Type",
        required=True,
        index=True,
    )

    tax_pis_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax PIS",
        domain=[("tax_domain", "=", TAX_DOMAIN_PIS)],
    )

    tax_pis_st_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax PIS ST",
        domain=[("tax_domain", "=", TAX_DOMAIN_PIS_ST)],
    )

    tax_cofins_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax COFINS",
        domain=[("tax_domain", "=", TAX_DOMAIN_COFINS)],
    )

    tax_cofins_st_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax COFINS ST",
        domain=[("tax_domain", "=", TAX_DOMAIN_COFINS_ST)],
    )

    ncms = fields.Char(string="NCM")

    ncm_exception = fields.Char(string="NCM Exeption")

    not_in_ncms = fields.Char(string="Not in NCM")

    ncm_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.ncm",
        relation="fiscal_pis_cofins_ncm_rel",
        column1="piscofins_id",
        column2="ncm_id",
        compute="_compute_ncms",
        store=True,
        readonly=True,
        string="NCMs",
    )

    @api.depends("ncms")
    def _compute_ncms(self):
        ncm = self.env["l10n_br_fiscal.ncm"]
        for r in self:
            domain = []

            # Clear Field to recompute
            r.ncm_ids = False
            if r.ncms:
                domain = tools.domain_field_codes(r.ncms)

            if r.not_in_ncms:
                domain += tools.domain_field_codes(
                    field_codes=r.not_in_ncms, operator1="!=", operator2="not ilike"
                )

            if r.ncm_exception:
                domain += tools.domain_field_codes(
                    field_codes=r.ncm_exception, field_name="exception", code_size=2
                )

            if domain:
                r.ncm_ids = ncm.search(domain)
