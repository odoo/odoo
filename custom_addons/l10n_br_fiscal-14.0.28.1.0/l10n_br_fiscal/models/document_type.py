# Copyright (C) 2009  Renato Lima - Akretion <renato.lima@akretion.com.br>
# Copyright (C) 2014  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import fields, models

from ..constants.fiscal import DOCUMENT_TYPE


class DocumentType(models.Model):
    _name = "l10n_br_fiscal.document.type"
    _description = "Fiscal Document Type"
    _inherit = "l10n_br_fiscal.data.abstract"

    code = fields.Char(
        size=8,
    )

    name = fields.Char(
        size=128,
    )

    electronic = fields.Boolean(
        string="Is Electronic?",
    )

    prefix = fields.Char()

    sufix = fields.Char()

    type = fields.Selection(
        selection=DOCUMENT_TYPE,
        string="Document Type",
        required=True,
    )

    document_email_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document.email",
        inverse_name="document_type_id",
        string="Email Template Definition",
    )

    document_serie_ids = fields.One2many(
        comodel_name="l10n_br_fiscal.document.serie",
        inverse_name="document_type_id",
        string="Document Series",
    )

    def _get_default_document_serie(self, company):
        """Overwrite this method in a custom fiscal document
        modules like l10n_br_nfe, l10n_br_nfse and etc, to
        return a especific fiscal document serie"""
        document_serie = self.env["l10n_br_fiscal.document.serie"]
        return document_serie.search(
            [
                ("active", "=", True),
                ("company_id", "=", company.id),
                ("document_type_id", "=", self.id),
            ],
            limit=1,
        )

    def get_document_serie(self, company, fiscal_operation):
        self.ensure_one()
        serie = self.env["l10n_br_fiscal.document.serie"]
        if fiscal_operation:
            # Get document serie from fiscal operation
            serie = fiscal_operation.get_document_serie(company, self)

        if not serie:
            # Get try defini default serie
            serie = self._get_default_document_serie(company)

        return serie
