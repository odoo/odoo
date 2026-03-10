# Copyright (C) 2013  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..constants.fiscal import (
    EDOC_PURPOSE,
    EDOC_PURPOSE_NORMAL,
    FISCAL_COMMENT_DOCUMENT,
    FISCAL_IN_OUT_ALL,
    OPERATION_FISCAL_TYPE,
    OPERATION_FISCAL_TYPE_DEFAULT,
    OPERATION_STATE,
    OPERATION_STATE_DEFAULT,
)


class Operation(models.Model):
    _name = "l10n_br_fiscal.operation"
    _description = "Fiscal Operation"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    code = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    name = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    fiscal_operation_type = fields.Selection(
        selection=FISCAL_IN_OUT_ALL,
        string="Type",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    edoc_purpose = fields.Selection(
        selection=EDOC_PURPOSE,
        string="Finalidade",
        default=EDOC_PURPOSE_NORMAL,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    default_price_unit = fields.Selection(
        selection=[("sale_price", _("Sale Price")), ("cost_price", _("Cost Price"))],
        string="Default Price Unit?",
        default="sale_price",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    fiscal_type = fields.Selection(
        selection=OPERATION_FISCAL_TYPE,
        default=OPERATION_FISCAL_TYPE_DEFAULT,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    return_fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Return Operation",
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain="[('fiscal_operation_type', '!=', fiscal_operation_type), "
        "('fiscal_type', 'in', {'sale': ['sale_refund'], 'purchase': "
        "['purchase_refund'], 'other': ['return_in', 'return_out'],"
        "'return_in': ['return_out'], 'return_out': ['return_in']}.get("
        "fiscal_type, []))]",
        tracking=True,
    )

    inverse_fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Inverse Operation",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    state = fields.Selection(
        selection=OPERATION_STATE,
        default=OPERATION_STATE_DEFAULT,
        index=True,
        readonly=True,
        tracking=True,
        copy=False,
    )

    document_type_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.operation.document.type",
        inverse_name="fiscal_operation_id",
        string="Operation Document Types",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    line_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.operation.line",
        inverse_name="fiscal_operation_id",
        string="Operation Line",
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=True,
    )

    comment_ids = fields.Many2many(
        comodel_name="l10n_br_fiscal.comment",
        relation="l10n_br_fiscal_operation_comment_rel",
        column1="fiscal_operation_id",
        column2="comment_id",
        domain=[("object", "=", FISCAL_COMMENT_DOCUMENT)],
        string="Comment",
    )

    operation_subsequent_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.subsequent.operation",
        inverse_name="fiscal_operation_id",
        string="Subsequent Operation",
    )

    _sql_constraints = [
        (
            "fiscal_operation_code_uniq",
            "unique (code)",
            _("Fiscal Operation already exists with this code !"),
        )
    ]

    def action_review(self):
        self.write({"state": "review"})
        self.line_ids.write({"state": "review"})

    def action_approve(self):
        self.write({"state": "approved"})
        self.line_ids.write({"state": "approved"})

    def action_draft(self):
        self.write({"state": "draft"})
        self.line_ids.write({"state": "draft"})

    def unlink(self):
        operations = self.filtered(lambda line: line.state == "approved")
        if operations:
            raise UserError(_("You cannot delete an Operation which is not draft !"))
        return super().unlink()

    def get_document_serie(self, company, document_type):
        self.ensure_one()
        serie = self.env["l10n_br_fiscal.document.serie"]
        document_type_serie = self.env["l10n_br_fiscal.operation.document.type"].search(
            [
                ("fiscal_operation_id", "=", self.id),
                ("company_id", "=", company.id),
                ("document_type_id", "=", document_type.id),
            ],
            limit=1,
        )

        if document_type_serie:
            serie = document_type_serie.document_serie_id

        return serie

    def _line_domain(self, company, partner, product):
        domain = [
            ("fiscal_operation_id", "=", self.id),
            ("fiscal_operation_type", "=", self.fiscal_operation_type),
            ("state", "=", "approved"),
        ]

        domain += [
            "|",
            ("date_start", "=", False),
            ("date_start", "<=", fields.Datetime.now()),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", fields.Datetime.now()),
        ]

        domain += [
            "|",
            ("company_tax_framework", "=", company.tax_framework),
            ("company_tax_framework", "=", False),
        ]

        domain += [
            "|",
            ("ind_ie_dest", "=", partner.ind_ie_dest),
            ("ind_ie_dest", "=", False),
        ]

        domain += [
            "|",
            ("partner_tax_framework", "=", partner.tax_framework),
            ("partner_tax_framework", "=", False),
        ]

        domain += [
            "|",
            ("product_type", "=", product.fiscal_type),
            ("product_type", "=", False),
        ]

        domain += [
            "|",
            ("tax_icms_or_issqn", "=", product.tax_icms_or_issqn),
            ("tax_icms_or_issqn", "=", False),
        ]

        domain += [
            "|",
            ("icms_origin", "=", product.icms_origin),
            ("icms_origin", "=", False),
        ]

        return domain

    def line_definition(self, company, partner, product):
        self.ensure_one()
        if not company:
            company = self.env.company

        lines = self.line_ids.search(self._line_domain(company, partner, product))

        return self._select_best_line(lines)

    def _select_best_line(self, lines):
        if not lines:
            return self.env["l10n_br_fiscal.operation.line"]

        def score(line):
            fields = [
                "company_tax_framework",
                "ind_ie_dest",
                "partner_tax_framework",
                "product_type",
                "tax_icms_or_issqn",
                "icms_origin",
            ]
            return sum(1 for field in fields if getattr(line, field))

        best_line = max(lines, key=score)
        return best_line

    @api.onchange("operation_subsequent_ids")
    def _onchange_operation_subsequent_ids(self):
        for sub_operation in self.operation_subsequent_ids:
            sub_operation.fiscal_operation_id = self.id

    def copy(self, default=None):
        """
        Inherit copy to edit field code. This is needed because the field is
        Unique and Required.
        """
        self.ensure_one()
        if default is None:
            default = {}
        if self.code:
            default["code"] = self.code + _(" (Copy)")

        res = super().copy(default)
        return res
