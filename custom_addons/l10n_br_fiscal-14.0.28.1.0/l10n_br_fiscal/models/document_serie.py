# Copyright (C) 2009  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2014  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models

from ..constants.fiscal import (
    DOCUMENT_ISSUER_COMPANY,
    FISCAL_IN_OUT,
    FISCAL_IN_OUT_DEFAULT,
)


class DocumentSerie(models.Model):
    _name = "l10n_br_fiscal.document.serie"
    _description = "Fiscal Document Serie"
    _inherit = "l10n_br_fiscal.data.abstract"

    code = fields.Char(size=3)

    name = fields.Char(required=True)

    active = fields.Boolean(default=True)

    fiscal_type = fields.Selection(
        selection=FISCAL_IN_OUT, string="Type", default=FISCAL_IN_OUT_DEFAULT
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        string="Fiscal Document",
        required=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    internal_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        domain="[('company_id', '=', company_id)]",
        string="Sequence",
    )

    sequence_number_next = fields.Integer(
        related="internal_sequence_id.number_next",
    )

    invalidate_number_id = fields.One2many(
        comodel_name="l10n_br_fiscal.invalidate.number",
        inverse_name="document_serie_id",
        string="Invalidate Number Range",
    )

    @api.model
    def _create_sequence(self, values):
        """Create new no_gap entry sequence for every
        new document serie"""
        sequence = {
            "name": values.get("name", _("Document Serie Sequence")),
            "implementation": "no_gap",
            "padding": 1,
            "number_increment": 1,
        }
        if "company_id" in values:
            sequence["company_id"] = values["company_id"]
        return self.env["ir.sequence"].create(sequence).id

    @api.model_create_multi
    def create(self, vals_list):
        """Overwrite method to create a new ir.sequence if
        this field is null"""
        for vals in vals_list:
            if not vals.get("internal_sequence_id"):
                vals.update({"internal_sequence_id": self._create_sequence(vals)})
        return super().create(vals_list)

    def name_get(self):
        return [(r.id, f"{r.name}") for r in self]

    def _is_invalid_number(self, document_number):
        self.ensure_one()
        is_invalid_number = True
        # TODO Improve this implementation!
        invalids = self.env["l10n_br_fiscal.invalidate.number"].search(
            [("state", "=", "done"), ("document_serie_id", "=", self.id)]
        )
        invalid_numbers = []
        for invalid in invalids:
            invalid_numbers += range(invalid.number_start, invalid.number_end + 1)
        if int(document_number) not in invalid_numbers:
            is_invalid_number = False
        return is_invalid_number

    def next_seq_number(self):
        self.ensure_one()
        document_number = self.internal_sequence_id._next()
        if self._is_invalid_number(document_number) or self.check_number_in_use(
            document_number
        ):
            document_number = self.next_seq_number()
        return document_number

    def check_number_in_use(self, document_number):
        """Check if a document with the same number already exists, this can
        happen in some cases, for example invoices imported in Odoo from another ERP."""

        return (
            self.env["l10n_br_fiscal.document"]
            .search(
                [
                    ("document_number", "=", document_number),
                    ("document_serie_id", "=", self.id),
                    ("document_type_id", "=", self.document_type_id.id),
                    ("issuer", "=", DOCUMENT_ISSUER_COMPANY),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            .exists()
        )
