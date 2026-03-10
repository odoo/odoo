# Copyright 2025 Marcel Savegnago <https://escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from ..constants.fiscal import (
    TAX_DOMAIN_CBS,
    TAX_DOMAIN_IBS,
    TAX_RATE_TYPE,
    TAX_RATE_TYPE_DEFAULT,
)


class TaxClassification(models.Model):
    _name = "l10n_br_fiscal.tax.classification"
    _inherit = "l10n_br_fiscal.data.abstract"
    _order = "code"
    _description = "Tax Classification"

    code = fields.Char(size=8)

    description = fields.Text()

    cst_code_prefix_like = fields.Char(
        compute="_compute_cst_code_prefix_like",
        help="Helper field to filter taxes by CST code prefix (3 chars) using LIKE.",
    )

    @api.depends("code")
    def _compute_cst_code_prefix_like(self):
        for rec in self:
            prefix = (rec.code or "")[:3]
            # Avoid matching all records when the prefix is not available yet.
            rec.cst_code_prefix_like = (
                f"{prefix}%" if len(prefix) == 3 else "__no_match__%"
            )

    tax_ibs_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax IBS",
        domain=(
            f"[('tax_domain', '=', '{TAX_DOMAIN_IBS}'), '|', "
            "('cst_in_id.code', 'like', cst_code_prefix_like), "
            "('cst_out_id.code', 'like', cst_code_prefix_like)]"
        ),
    )

    tax_cbs_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.tax",
        string="Tax CBS",
        domain=(
            f"[('tax_domain', '=', '{TAX_DOMAIN_CBS}'), '|', "
            "('cst_in_id.code', 'like', cst_code_prefix_like), "
            "('cst_out_id.code', 'like', cst_code_prefix_like)]"
        ),
    )

    regular_taxation = fields.Boolean(
        default=False,
    )

    presumed_credit = fields.Boolean(
        default=False,
    )

    credit_reversal = fields.Boolean(
        default=False,
    )

    rate_type = fields.Selection(
        selection=TAX_RATE_TYPE,
        default=TAX_RATE_TYPE_DEFAULT,
        required=True,
    )

    document_type_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.document.type",
        relation="tax_classification_document_type_rel",
        string="Related DFes",
        help="Related Digital Fiscal Documents",
    )
