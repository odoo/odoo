# Copyright (C) 2013  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models

from ..constants.fiscal import FISCAL_IN, FISCAL_OUT, TAX_DOMAIN_IPI
from ..constants.ipi import IPI_GUIDELINE_GROUP


class TaxIpiGuideline(models.Model):
    _name = "l10n_br_fiscal.tax.ipi.guideline"
    _description = "IPI Guidelines"
    _inherit = "l10n_br_fiscal.data.abstract"

    code = fields.Char(size=3)

    cst_group = fields.Selection(
        selection=IPI_GUIDELINE_GROUP, string="Group", required=True
    )

    cst_in_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cst",
        domain=[("domain", "=", TAX_DOMAIN_IPI), ("cst_type", "=", FISCAL_IN)],
        string="CST In",
    )

    cst_out_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.cst",
        domain=[("domain", "=", TAX_DOMAIN_IPI), ("cst_type", "=", FISCAL_OUT)],
        string="CST Out",
    )
