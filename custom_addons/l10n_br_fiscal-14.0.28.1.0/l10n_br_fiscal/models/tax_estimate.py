# Copyright (C) 2012  Renato Lima - Akretion <renato.lima@akretion.com.br>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class TaxEstimate(models.Model):
    _name = "l10n_br_fiscal.tax.estimate"
    _description = "Fiscal Tax Estimate"
    _order = "create_date desc"

    ncm_id = fields.Many2one(comodel_name="l10n_br_fiscal.ncm", string="NCM")

    nbs_id = fields.Many2one(comodel_name="l10n_br_fiscal.nbs", string="NBS")

    state_id = fields.Many2one(
        comodel_name="res.country.state", string="State", required=True
    )

    federal_taxes_national = fields.Float(
        string="Impostos Federais Nacional",
        digits="Fiscal Tax Percent",
    )

    federal_taxes_import = fields.Float(
        string="Impostos Federais Importado",
        digits="Fiscal Tax Percent",
    )

    state_taxes = fields.Float(
        string="Impostos Estaduais Nacional",
        digits="Fiscal Tax Percent",
    )

    municipal_taxes = fields.Float(
        string="Impostos Municipais Nacional",
        digits="Fiscal Tax Percent",
    )

    create_date = fields.Datetime(readonly=True)

    key = fields.Char(size=32)

    origin = fields.Char(string="Source", size=32)

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
