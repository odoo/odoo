from typing import Any

from odoo import api, fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.mixin_catalog import name_uniq_index

_debug = DebugLog(__name__)


class DocumentType(models.Model):
    _name = "document.type"
    _inherit = ["mixin.catalog"]
    _description = "Document Type"
    _order = "sequence, name"

    name = fields.Char(
        help="Name of this document type (e.g., 'Passport', 'Driver License', 'Work Permit')"
    )
    code = fields.Char(
        required=True,
        help="Short code for this document type (e.g., 'PASSPORT', 'DL', 'WP')",
    )
    active = fields.Boolean(
        help="Uncheck to archive this document type without deleting it"
    )
    sequence = fields.Integer(
        default=10,
        help="Used to order document types in lists and menus (lower numbers appear first)",
    )
    description = fields.Text(
        translate=True,
        help="Detailed description of this document type and its purpose",
    )

    has_expiration = fields.Boolean(
        default=True,
        help="Check if documents of this type have an expiration date",
    )
    default_validity_days = fields.Integer(
        help="Default number of days a new document of this type is valid for (e.g., 365 for annual permits)"
    )
    is_renewable = fields.Boolean(
        default=True,
        help="Check if documents of this type can be renewed when they expire",
    )

    tag_ids = fields.Many2many(
        comodel_name="document.tag",
        relation="document_type_tag_rel",
        column1="type_id",
        column2="tag_id",
        help="Tags that will be automatically applied to new documents of this type",
    )
    folder_id = fields.Many2one(
        comodel_name="document.document",
        domain="[('type', '=', 'folder')]",
        help="Default folder where documents of this type should be stored",
    )

    document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="document_type_id",
        help="Documents of this type",
    )
    document_count = fields.Integer(
        compute="_compute_document_counts",
        help="Total number of documents of this type",
    )
    expired_document_count = fields.Integer(
        compute="_compute_document_counts",
        help="Number of documents of this type that are currently expired",
    )
    expiring_soon_count = fields.Integer(
        compute="_compute_document_counts",
        help="Number of documents of this type expiring within the next 30 days",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Company this document type belongs to (leave empty for all companies)",
    )

    _code_company_uniq = models.UniqueIndex(
        "(code, company_id) NULLS NOT DISTINCT",
        "Document type code must be unique per company!",
    )

    _name_src_uniq = name_uniq_index(
        "company_id",
        message="A document type with this name already exists for this company.",
    )

    @api.depends("document_ids.expiration_state")
    def _compute_document_counts(self) -> None:
        data = self.env["document.document"]._read_group(
            [("document_type_id", "in", self.ids)],
            groupby=["document_type_id", "expiration_state"],
            aggregates=["__count"],
        )
        _debug.perf.count("document_type_counts", types=self, rows=len(data))
        totals: dict[int, int] = {}
        per_state: dict[tuple[int, str], int] = {}
        for doc_type, state, count in data:
            totals[doc_type.id] = totals.get(doc_type.id, 0) + count
            per_state[(doc_type.id, state)] = count

        for doc_type in self:
            doc_type.document_count = totals.get(doc_type.id, 0)
            doc_type.expired_document_count = per_state.get((doc_type.id, "expired"), 0)
            doc_type.expiring_soon_count = per_state.get(
                (doc_type.id, "expiring_soon"), 0
            )

    def action_view_documents(self) -> dict[str, Any]:
        self.check_singleton()

        domain = [("document_type_id", "=", self.id)]
        expiration_filter = self.env.context.get("expiration_filter")
        if expiration_filter:
            domain.append(("expiration_state", "=", expiration_filter))

        return {
            "name": self.env._("%(type)s Documents", type=self.name),
            "type": "ir.actions.act_window",
            "res_model": "document.document",
            "view_mode": "list,form",
            "domain": domain,
            "context": {
                "default_document_type_id": self.id,
                "default_folder_id": self.folder_id.id,
                "default_tag_ids": [Command.set(self.tag_ids.ids)],
            },
        }
