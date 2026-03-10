# Copyright 2020 - TODAY, Marcel Savegnago - Escodoo
# Copyright 2020 - TODAY, Renato Lima - Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from ..constants.fiscal import DOCUMENT_ISSUER, DOCUMENT_ISSUER_COMPANY, SITUACAO_EDOC


class DocumentEmail(models.Model):
    _name = "l10n_br_fiscal.document.email"
    _description = "Fiscal Document Email"

    name = fields.Char(
        readonly=True,
        store=True,
        copy=False,
        compute="_compute_name",
    )

    active = fields.Boolean(
        default=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
    )

    document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        string="Fiscal Document Type",
        help="Select the type of document that will be applied "
        "to the email templates definitions.",
    )

    issuer = fields.Selection(
        selection=DOCUMENT_ISSUER,
        default=DOCUMENT_ISSUER_COMPANY,
        required=True,
    )

    state_edoc = fields.Selection(
        selection=SITUACAO_EDOC,
        string="Situação e-doc",
        copy=False,
        index=True,
    )

    email_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Fiscal Document E-mail Template",
        required=True,
        domain=[("model", "=", "l10n_br_fiscal.document")],
        help="Select the email template that will be sent when "
        "this document state change.",
    )

    @api.depends("document_type_id", "state_edoc")
    def _compute_name(self):
        for record in self:
            document_type = record.document_type_id.name
            if not document_type:
                document_type = "Others Document Types"
            if record.state_edoc:
                record.name = document_type + " - " + record.state_edoc

    _sql_constraints = [
        (
            "name_company_unique",
            "unique(name)",
            "This name is already used by another email definition !",
        )
    ]
