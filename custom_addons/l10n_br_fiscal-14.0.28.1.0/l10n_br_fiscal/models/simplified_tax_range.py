# Copyright (C) 2019  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models


class SimplifiedTaxRange(models.Model):
    _name = "l10n_br_fiscal.simplified.tax.range"
    _description = "National Simplified Tax Range"
    _order = "name asc"

    name = fields.Char(required=True)

    simplified_tax_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.simplified.tax", string="Simplified Tax"
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency", string="Currency", required=True
    )

    amount_deduced = fields.Monetary(
        string="Amount to be Deducted",
        currency_field="currency_id",
        required=True,
    )

    inital_revenue = fields.Monetary(
        currency_field="currency_id",
    )

    final_revenue = fields.Monetary(
        currency_field="currency_id",
    )

    total_tax_percent = fields.Float(string="Tax Percent", digits="Fiscal Tax Percent")

    tax_cpp_percent = fields.Float(
        string="Tax CPP Percent", digits="Fiscal Tax Percent"
    )

    tax_csll_percent = fields.Float(
        string="Tax CSLL Percent", digits="Fiscal Tax Percent"
    )

    tax_ipi_percent = fields.Float(
        string="Tax IPI Percent", digits="Fiscal Tax Percent"
    )

    tax_icms_percent = fields.Float(
        string="Tax ICMS Percent", digits="Fiscal Tax Percent"
    )

    tax_iss_percent = fields.Float(
        string="Tax ISS Percent", digits="Fiscal Tax Percent"
    )

    tax_irpj_percent = fields.Float(
        string="Tax IRPJ Percent", digits="Fiscal Tax Percent"
    )

    tax_cofins_percent = fields.Float(
        string="Tax COFINS Percent", digits="Fiscal Tax Percent"
    )

    tax_pis_percent = fields.Float(
        string="Tax PIS Percent", digits="Fiscal Tax Percent"
    )

    tax_ibs_percent = fields.Float(
        string="Tax IBS Percent", digits="Fiscal Tax Percent"
    )

    tax_cbs_percent = fields.Float(
        string="Tax CBS Percent", digits="Fiscal Tax Percent"
    )
