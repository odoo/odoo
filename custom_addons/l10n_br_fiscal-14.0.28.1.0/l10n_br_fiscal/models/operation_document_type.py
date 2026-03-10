# Copyright (C) 2020  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class OperationDocumentType(models.Model):
    _name = "l10n_br_fiscal.operation.document.type"
    _description = "Fiscal Operation Document Type"

    fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Operation",
        ondelete="cascade",
        required=True,
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type", required=True
    )

    document_electronic = fields.Boolean(
        related="document_type_id.electronic", string="Electronic?"
    )

    document_serie_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.serie",
        company_dependent=True,
        domain="[('active', '=', True)," "('document_type_id', '=', document_type_id)]",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    name = fields.Char(
        compute="_compute_name",
    )

    @api.depends("document_type_id", "document_serie_id")
    def _compute_name(self):
        for record in self:
            document_serie = record.document_serie_id.name
            if not document_serie:
                document_serie = "Series not defined"
            record.name = record.document_type_id.name + " - " + document_serie
