from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.document.tools import UserFolder

_debug = DebugLog(__name__)


class DocumentsOperation(models.TransientModel):
    """Wizard to move, copy, shortcut or attach documents to a destination folder."""

    _name = "document.operation"
    _description = "Documents Operation"

    @api.model
    def default_get(self, fields: list[str]) -> dict:
        """Return the default values, computing the destination folder."""
        result = super().default_get(fields)
        if "destination" in fields and not result.get("destination"):
            if self.env.user.share:
                if first_folder := self.get_any_editor_destination():
                    result["destination"] = str(first_folder[0]["id"])
                    result["display_name"] = first_folder[0]["display_name"]
                else:
                    _debug.logic("operation_refused", reason="no_editable_folder")
                    raise UserError(
                        self.env._("You do not have editor access to any folder.")
                    )
            else:
                result["destination"] = UserFolder.MY
                result["display_name"] = self.env._("My Drive")
        return result

    operation = fields.Selection(
        selection=[
            ("move", "Move"),
            ("shortcut", "Create shortcuts"),
            ("copy", "Duplicate to"),
            ("add", "Add attachment to Documents"),
        ],
        required=True,
    )
    document_ids = fields.Many2many(
        comodel_name="document.document",
        string="Documents",
    )
    attachment_id = fields.Many2one(comodel_name="ir.attachment")

    destination = fields.Char(required=True)
    destination_children_ids = fields.One2many(
        comodel_name="document.document",
        string="Siblings",
        compute="_compute_destination_children_ids",
    )

    # Destination-related fields updated by the client for the client - do not use in the backend. No need
    # for compute/search because all is already fetched for the searchpanel and must be kept locally consistent
    display_name = fields.Char(
        string="Destination Display Name",
        compute=None,
        search=None,
    )
    user_permission = fields.Selection(
        selection=[("edit", "Editor"), ("view", "Viewer"), ("none", "None")],
        string="Destination User Permission",
        default="edit",
        required=True,
    )
    access_internal = fields.Char(string="Destination Access Internal")
    access_via_link = fields.Char(string="Destination Access Via Link")
    is_access_via_link_hidden = fields.Boolean(string="Destination Link Access Hidden")

    @api.depends("destination")
    def _compute_destination_children_ids(self) -> None:
        locations_to_targets = {}
        # `destination` is a `user_folder_id`: a real folder, or a virtual root
        # with no folder to look up. `.isnumeric()` on it also assumed a string,
        # which a wizard whose destination is not set yet is not.
        destinations = {wizard: UserFolder.parse(wizard.destination) for wizard in self}
        if wizards_with_folders_locations := self.filtered(
            lambda w: destinations[w] is not None and destinations[w].is_folder
        ):
            folders = self.env["document.document"].search_fetch(
                Domain(
                    "id",
                    "in",
                    [
                        destinations[wizard].folder_id
                        for wizard in wizards_with_folders_locations
                    ],
                ),
                ["shortcut_document_id"],
            )
            # Key by id, never by position: ``search_fetch`` returns rows in the
            # model's ``_order``, not in wizard order, and a missing folder
            # (unreadable or stale destination) would shift every later pair.
            folders_by_id = folders.grouped("id")
            for wizard in wizards_with_folders_locations:
                if folder := folders_by_id.get(destinations[wizard].folder_id):
                    locations_to_targets[wizard] = (
                        folder.shortcut_document_id.id or folder.id
                    )
        targets = {
            wizard: locations_to_targets.get(wizard) or wizard.destination
            for wizard in self
        }
        children = self.env["document.document"].search(
            Domain("user_folder_id", "in", list(set(targets.values())))
            & Domain("type", "!=", "folder")
        )
        # user_folder_id reads as a string (a folder id is its str), while a
        # resolved folder target is an int the search side accepts as well.
        by_target = children.grouped("user_folder_id")
        for wizard in self:
            target = targets[wizard]
            wizard.destination_children_ids = by_target.get(
                str(target) if isinstance(target, int) else target, children.browse()
            )

    def action_confirm(self) -> None:
        """Execute the selected operation on the documents."""
        self.check_singleton()
        _debug.pipeline(
            "operation",
            by=self.operation,
            documents=self.document_ids,
            destination=self.destination,
        )
        if self.operation == "move":
            self.document_ids.user_folder_id = self.destination
        elif self.operation == "copy":
            self.document_ids.copy({"user_folder_id": self.destination})
        elif self.operation == "add":
            if not self.attachment_id:
                _debug.logic("operation_refused", reason="no_attachment")
                raise UserError(self.env._("No attachment to add."))
            if self.attachment_id.type not in dict(
                self.env["document.document"]._fields["type"].selection
            ):
                _debug.logic(
                    "operation_refused",
                    reason="bad_attachment_type",
                    type=self.attachment_id.type,
                )
                raise UserError(
                    self.env._(
                        "Unsupported attachment type: %s", self.attachment_id.type
                    )
                )
            attachment_copy = self.attachment_id.copy(
                {"res_model": False, "res_id": False}
            )
            values = {
                "attachment_id": attachment_copy.id,
                "type": attachment_copy.type,
                "user_folder_id": self.destination,
            }
            if attachment_copy.type == "url":
                # A `document.document` of type url keeps its address in its OWN
                # `url` field; an `ir.attachment` keeps it in the attachment's.
                # Copying only the type produced a url document with no url --
                # `_is_safe_redirect_url(False)` is False, so `/documents/content`
                # answered 404 and the entry pointed nowhere, silently.
                #
                # Carrying it also re-imposes `_check_url`, which is the point
                # rather than a side effect: a document url must be complete, so
                # an attachment holding a relative one (`/web/content/42`, which
                # is how Odoo links its own files) is now refused with that
                # constraint's own message instead of becoming a broken entry.
                values["url"] = attachment_copy.url
            self.env["document.document"].create(values)
        elif self.operation == "shortcut":
            self.document_ids.action_create_shortcut(
                location_user_folder_id=self.destination
            )
        else:
            _debug.logic("operation_refused", reason="unknown", by=self.operation)
            raise UserError(self.env._("Invalid operation"))

    @api.readonly
    @api.model
    def get_any_editor_destination(self) -> list:
        """Return one folder the user has editor access to, if any."""
        return self.env["document.document"].search_read(
            [
                ("type", "=", "folder"),
                ("shortcut_document_id", "=", False),
                ("user_permission", "=", "edit"),
            ],
            ["id", "display_name"],
            limit=1,
        )
