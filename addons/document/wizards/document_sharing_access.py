from odoo import api, fields, models


class DocumentsShareAccess(models.TransientModel):
    """Per-partner access line displayed inside the documents sharing wizard."""

    _name = "document.sharing.access"
    _description = "Documents share access"

    documents_sharing_id = fields.Many2one(
        comodel_name="document.sharing",
        string="Documents share",
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        ondelete="cascade",
    )

    # Rights edition
    role = fields.Selection(
        selection="_selection_access_roles",
        required=True,
    )
    expiration_date = fields.Datetime(string="Expiration")
    original_expiration_date = fields.Datetime(string="Original Expiration")
    is_deleted = fields.Boolean()

    # Additional readonly fields for displaying information
    partner_is_me = fields.Boolean(
        string="Is me",
        compute="_compute_partner_is_me",
    )

    # Edition flags
    has_user = fields.Boolean(compute="_compute_has_user")
    has_warning_no_access = fields.Boolean(compute="_compute_has_warning_no_access")
    is_on_single_document = fields.Boolean(compute="_compute_is_on_single_document")
    is_readonly = fields.Boolean(related="documents_sharing_id.is_readonly")

    @api.model
    def _selection_access_roles(self) -> list:
        return self.env["document.sharing"]._selection_access_roles()

    @api.depends_context("uid")
    @api.depends("partner_id")
    def _compute_partner_is_me(self) -> None:
        me = self.env.user.partner_id
        for record in self:
            record.partner_is_me = record.partner_id == me

    @api.depends("documents_sharing_id.document_ids")
    def _compute_is_on_single_document(self) -> None:
        for record in self:
            record.is_on_single_document = record.documents_sharing_id.is_single

    @api.depends("partner_id.user_ids")
    def _compute_has_user(self) -> None:
        for record in self:
            record.has_user = bool(record.partner_id.user_ids)

    @api.depends(
        "documents_sharing_id.access_via_link",
        "documents_sharing_id.invite_partner_ids",
        "partner_id.user_ids",
    )
    def _compute_has_warning_no_access(self) -> None:
        for record in self:
            record.has_warning_no_access = (
                not record.documents_sharing_id.invite_partner_ids  # we are modifying rights not inviting
                and record.documents_sharing_id.access_via_link.endswith("none")
                and not record.has_user
            )
