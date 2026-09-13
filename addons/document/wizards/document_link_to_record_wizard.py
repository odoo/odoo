from odoo import api, fields, models
from odoo.exceptions import UserError


class DocumentsLink_To_Record_Wizard(models.TransientModel):
    """Wizard to link documents to a record of another mail-thread model."""

    _name = "document.link_to_record_wizard"
    _description = "Documents Link to Record"

    def _domain_model_id(self) -> list:
        models = self.env["ir.model.access"]._get_models_allowed() - {
            "document.document"
        }
        return [("model", "in", list(models)), ("is_mail_thread", "=", True)]

    @api.model
    def _selection_target_model(self) -> list:
        return [
            (model.model, model.name)
            for model in self.env["ir.model"]
            .sudo()
            .search(
                [("model", "!=", "document.document"), ("is_mail_thread", "=", True)]
            )
        ]

    document_ids = fields.Many2many(
        comodel_name="document.document",
        string="Documents",
        readonly=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        domain=_domain_model_id,
    )
    is_readonly_model = fields.Boolean(
        string="is_readonly_model",
        default=True,
    )
    resource_ref = fields.Reference(
        selection="_selection_target_model",
        string="Record",
    )

    def link_to(self) -> None:
        """Link the selected documents to the chosen record."""
        self.check_singleton()
        if not self.resource_ref:
            # UI-unreachable (the button is ``invisible="not resource_ref"``)
            # but the method is RPC-callable, where it raised AttributeError.
            raise UserError(self.env._("Please select a record to link to."))
        # Enforce write access on the *specific* target record: the model-level
        # filtering (_domain_model_id) is UI-only, so without this a documents
        # user could link documents onto any record id of any mail-thread model.
        self.resource_ref.check_access("write")
        self.document_ids.with_company(self.env.company).write(
            {
                "res_model": self.resource_ref._name,
                "res_id": self.resource_ref.id,
                "is_editable_attachment": True,
            }
        )
