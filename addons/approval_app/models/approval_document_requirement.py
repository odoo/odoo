from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class ApprovalDocumentRequirement(models.Model):
    _name = "approval.document.requirement"
    _description = "Approval Document Requirement"
    _order = "category_id, sequence"

    _name_src_uniq = name_uniq_index(
        "category_id",
        nulls_distinct=True,
        message="Document requirement name must be unique per category.",
    )

    name = fields.Char(
        translate=True,
        required=True,
        help="Document type name (e.g. 'Invoice PDF', 'Vendor Quote'). A "
        "LABEL, translatable for the ordinary reason: the requester picks "
        "it from a dropdown on the file they upload. It used to be "
        "load-bearing — the confirm-time check matched it as a substring "
        "of the uploaded file NAMES, so an untranslated value silently "
        "forced requesters to name their files in whatever language the "
        "category was configured in, and on an es_MX deployment "
        "'Factura.pdf' failed a requirement called 'Invoice' with an error "
        "telling the user to rename their file. The link is structural now "
        "(ir.attachment.approval_requirement_id), so the name means "
        "nothing to the check — and the cross-language uniqueness "
        "constraint that matching needed is gone with it.",
    )
    category_id = fields.Many2one(
        comodel_name="approval.category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    required = fields.Boolean(
        default=True,
        help="If checked, this document must be attached before submission",
    )
    description = fields.Text(help="Instructions for the requester about this document")
