from odoo import Command, _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentsSharing(models.TransientModel):
    """Wizard to review and edit sharing rights of one or more documents."""

    _name = "document.sharing"
    _description = "Documents Sharing"

    document_ids = fields.Many2many(
        comodel_name="document.document",
        readonly=True,
        ondelete="cascade",
    )
    share_access_ids = fields.One2many(
        comodel_name="document.sharing.access",
        inverse_name="documents_sharing_id",
        required=True,
    )

    # Rights edition
    access_internal = fields.Selection(
        selection="_selection_access_roles",
        string="Internal users",
        required=True,
    )
    access_internal_help = fields.Char(compute="_compute_access_internal_help")
    access_via_link = fields.Selection(
        selection="_selection_access_roles",
        string="Access through link",
        required=True,
    )
    access_via_link_help = fields.Char(compute="_compute_access_via_link_help")
    access_via_link_mode = fields.Selection(
        selection="_selection_access_via_link_mode",
        string="Discoverable",
        required=True,
    )
    viewer_download_mode = fields.Selection(
        selection="_selection_viewer_download_mode",
        string="Viewers can download",
        required=True,
    )
    is_access_modified = fields.Boolean(
        string="Modified",
        compute="_compute_is_access_modified",
    )

    # Invitation
    invite_role = fields.Selection(
        selection=[("view", "Viewer"), ("edit", "Editor")],
        string="Role",
        default="view",
        required=True,
    )
    invite_notify = fields.Boolean(
        string="Notify",
        default=True,
    )
    invite_notify_message = fields.Html(string="Notification Message")
    invite_partner_ids = fields.Many2many(comodel_name="res.partner")

    # Additional readonly fields for displaying information
    access_urls = fields.Char(
        string="Access URLs",
        compute="_compute_ui_values",
    )
    is_single = fields.Boolean(
        string="Single",
        compute="_compute_ui_values",
    )
    is_folder_only = fields.Boolean(
        string="Folder Only",
        compute="_compute_ui_values",
    )
    is_readonly = fields.Boolean(
        string="Readonly",
        compute="_compute_ui_values",
    )
    has_warning_link_with_more_rights = fields.Boolean(
        compute="_compute_has_warning_link_with_more_rights"
    )
    has_warning_partners_without_access = fields.Boolean(
        compute="_compute_has_warning_partners_without_access"
    )
    has_warning_self_access_loss = fields.Boolean(
        compute="_compute_has_warning_self_access_loss"
    )
    owner_id = fields.Many2one(
        comodel_name="res.users",
        string="Owner of all documents",
        compute="_compute_ui_values",
    )

    WRITE_VALUE_PREFIX = "write_"

    @api.model
    def _add_write_options(self, selection_options: list) -> list:
        """Add write options to the given options list.

        For each existing option, adds a corresponding option with the prefix WRITE_VALUE_PREFIX (except for "mixed").
        Selecting a 'write_' option indicates that a change has been made.
        """
        new_options = []
        for code, label in selection_options:
            new_options.append((code, label))
            if code != "mixed":
                new_options.append((f"{self.WRITE_VALUE_PREFIX}{code}", label))
        return new_options

    @api.model
    def _selection_access_roles(self) -> list:
        return self._add_write_options(
            [
                ("view", _("Viewer")),
                ("edit", _("Editor")),
                ("none", _("None")),
                ("mixed", _("Mixed rights")),
            ]
        )

    @api.model
    def _selection_access_via_link_mode(self) -> list:
        return self._add_write_options(
            [
                ("mixed", _("Mixed values")),
                ("link_required", _("No")),
                ("discoverable", _("Yes")),
            ]
        )

    @api.model
    def _selection_viewer_download_mode(self) -> list:
        return self._add_write_options(
            [
                ("mixed", _("Mixed values")),
                ("blocked", _("No")),
                ("allowed", _("Yes")),
            ]
        )

    @api.depends_context("uid")
    @api.depends("document_ids")
    def _compute_ui_values(self) -> None:
        for record in self:
            documents = record.document_ids
            document0 = documents[:1]
            record.is_single = len(documents) == 1
            record.access_urls = ", ".join(d.access_url for d in documents)
            owner_is_multi = any(d.owner_id != document0.owner_id for d in documents)
            record.owner_id = document0.owner_id if not owner_is_multi else False
            record.is_folder_only = all(d.type == "folder" for d in documents)
            record.is_readonly = any(d.user_permission != "edit" for d in documents)

    @api.depends(
        "access_internal",
        "access_via_link",
        "access_via_link_mode",
        "viewer_download_mode",
        "share_access_ids",
        "share_access_ids.role",
        "share_access_ids.original_expiration_date",
        "share_access_ids.expiration_date",
        "share_access_ids.is_deleted",
    )
    def _compute_is_access_modified(self) -> None:
        for record in self:
            record.is_access_modified = bool(record._get_update_rights_params())

    def action_update_rights(self) -> dict:
        """Apply the edited access rights and reopen the sharing wizard."""
        self.check_singleton()
        _debug.pipeline(
            "sharing_apply",
            documents=self.document_ids,
            propagate=bool(self.is_folder_only),
        )
        self.document_ids.action_update_access_rights(
            **self._get_update_rights_params(), no_propagation=not self.is_folder_only
        )
        # The confirmed change may have removed the current user's own access
        # (advisory `has_warning_self_access_loss`). Reopening the wizard on a
        # now-inaccessible document would raise AccessError while building its
        # document_ids, so only reopen on documents still readable.
        accessible = self.document_ids._filtered_access("read")
        if not accessible:
            _debug.logic("sharing_self_access_lost", documents=self.document_ids)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "message": _("Access rights updated."),
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return self.action_open(accessible.ids)

    def action_invite_members(self) -> dict:
        """Invite the selected partners and optionally notify them by email."""
        self.check_singleton()
        if not self.invite_partner_ids:
            _debug.logic("invite_refused", reason="no_partners")
            params = {
                "title": _("No partners"),
                "message": "",
                "type": "warning",
            }
        elif self.invite_partner_ids.filtered(lambda p: not p.email):
            _debug.logic("invite_refused", reason="missing_email")
            params = {
                "title": _("Some emails are missing"),
                "message": _("Please fill in the missing email addresses."),
                "type": "warning",
            }
        else:
            _debug.lifecycle(
                "invite",
                documents=self.document_ids,
                partners=self.invite_partner_ids,
                role=self.invite_role,
                notify=self.invite_notify,
            )
            self.document_ids.action_update_access_rights(
                partners=dict.fromkeys(
                    self.invite_partner_ids, (self.invite_role, None)
                ),
                no_propagation=not self.is_folder_only,
            )
            if self.invite_notify and (
                share_template := self.env.ref(
                    "document.mail_template_document_share", raise_if_not_found=False
                )
            ):
                access_urls_by_partner = {}
                for partner in self.invite_partner_ids:
                    access_urls = {}
                    for document in self.document_ids:
                        access_url = document.access_url
                        member = document.access_ids.filtered(
                            lambda access, partner=partner: access.partner_id == partner
                        )
                        if member and member._is_signup_available():
                            access_url = f"{access_url}?member_signup_token={member._get_member_signup_token()}&member_id={member.id}"
                        access_urls[document] = access_url
                    access_urls_by_partner[partner] = access_urls
                with _debug.perf(
                    "invite_mail_sent",
                    cr=self.env.cr,
                    partners=self.invite_partner_ids,
                ):
                    share_template.with_context(
                        documents=self.document_ids,
                        access_urls_by_partner=access_urls_by_partner,
                        message=self.invite_notify_message or "",
                    ).send_mail_batch(self.invite_partner_ids.ids)

            params = {
                "title": _("Successfully Shared"),
                "message": (
                    _("%s members added.", len(self.invite_partner_ids))
                    if len(self.invite_partner_ids) > 1
                    else _("Member added.")
                ),
                "type": "success",
                "next": self.action_open(self.document_ids.ids),
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": params,
        }

    def action_allow_link_access(self) -> dict:
        """Enable link access when needed and apply the edited rights."""
        self.check_singleton()
        if self.has_warning_partners_without_access:
            _debug.logic("link_access_forced", documents=self.document_ids)
            self.access_via_link = f"{self.WRITE_VALUE_PREFIX}view"
            self.access_via_link_mode = f"{self.WRITE_VALUE_PREFIX}link_required"
        return self.action_update_rights()

    @api.model
    def action_open(self, document_ids: list[int]) -> dict:
        """Open documents sharing wizard on one or more documents."""
        if not document_ids:
            _debug.logic("sharing_open_refused", reason="no_documents")
            raise ValueError("Expected one or more documents.")
        documents = (
            self.env["document.document"]
            .browse(document_ids)
            .mapped(lambda d: d.shortcut_document_id or d)
        )
        document0 = documents[0]

        is_single_doc = len(documents) == 1
        all_partners = self._filtered_relevant_access(documents).partner_id
        access_by_partner_by_doc = {
            doc: {
                access.partner_id: access.role
                for access in self._filtered_relevant_access(doc)
            }
            | ({doc.owner_id.partner_id: "edit"} if doc.owner_id else {})
            for doc in documents
        }

        if is_single_doc:  # expiration only supported for single document
            expiration_per_partner = {
                access.partner_id: access.expiration_date
                for access in self._filtered_relevant_access(documents)
            }

        access_shares = []
        if any(
            d.owner_id != document0.owner_id for d in documents
        ):  # there are no single owner of all the documents
            # Mixed owner -> add owner so that their rights appear "mixed" if not editor of the documents they don't own
            # Otherwise if there are only one owner, it will be displayed as such
            all_partners |= documents.owner_id.partner_id
        for partner in all_partners:
            role0 = access_by_partner_by_doc.get(documents[0], {}).get(partner)
            is_mixed = any(
                role0 != access_by_partner_by_doc.get(doc, {}).get(partner)
                for doc in documents[1:]
            )
            expiration_date = (
                expiration_per_partner.get(partner) if is_single_doc else False
            )
            access_shares.append(
                Command.create(
                    {
                        "expiration_date": expiration_date,
                        "original_expiration_date": expiration_date,
                        "partner_id": partner.id,
                        "role": "mixed" if is_mixed else role0,
                    }
                )
            )

        values = {
            field: document0[field]
            if len(set(documents.mapped(field))) == 1
            else "mixed"
            for field in ("access_internal", "access_via_link")
        }
        if len(set(documents.mapped("is_access_via_link_hidden"))) != 1:
            values["access_via_link_mode"] = "mixed"
        elif document0.is_access_via_link_hidden:
            values["access_via_link_mode"] = "link_required"
        else:
            values["access_via_link_mode"] = "discoverable"

        if len(set(documents.mapped("is_download_blocked"))) != 1:
            values["viewer_download_mode"] = "mixed"
        elif document0.is_download_blocked:
            values["viewer_download_mode"] = "blocked"
        else:
            values["viewer_download_mode"] = "allowed"

        _debug.pipeline(
            "sharing_open",
            documents=documents,
            members=len(access_shares),
            mixed=sorted(k for k, v in values.items() if v == "mixed"),
        )
        doc_sharing = self.env["document.sharing"].create(
            [
                {
                    "document_ids": documents.ids,
                    "share_access_ids": access_shares,
                    **values,
                }
            ]
        )

        if len(documents) == 1:
            name = _("Share: %(documentName)s", documentName=documents.name)
        else:
            name = _(
                "Share: %(numberOfDocuments)s files", numberOfDocuments=len(documents)
            )
        return {
            "context": {
                "dialog_size": "medium",
            },
            "name": name,
            "res_id": doc_sharing.id,
            "res_model": "document.sharing",
            "target": "new",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [[False, "form"]],
        }

    @api.model
    def _filtered_relevant_access(self, documents: models.Model) -> models.Model:
        """Filter out expired access and non access of the documents (logs: role == False, owner access)."""
        return documents.access_ids.filtered(
            lambda a: (
                a.role
                and a.partner_id != a.document_id.owner_id.partner_id
                and (
                    not a.expiration_date or a.expiration_date >= fields.Datetime.now()
                )
            )
        )

    def _get_update_rights_params(self) -> dict:
        self.check_singleton()
        res = {}
        removed_access = self.share_access_ids.filtered("is_deleted")
        # Modification of the expiration date is not supported when multiple document are selected
        # In that case, expiration_date and original_expiration_date will be false and not modifiable in the UI
        # If a role is changed when multiple documents are selected, we keep the expiration (using None).
        modified_access = self.share_access_ids.filtered(
            lambda a: (
                (
                    a.role.startswith(self.WRITE_VALUE_PREFIX)
                    or a.expiration_date != a.original_expiration_date
                )
                and not a.is_deleted
            )
        )
        partners = {
            access.partner_id: (
                access.role.removeprefix(self.WRITE_VALUE_PREFIX),
                access.expiration_date if self.is_single else None,
            )
            for access in modified_access
        }
        partners.update(
            {access.partner_id: (False, False) for access in removed_access}
        )
        if partners:
            _debug.logic(
                "sharing_params",
                modified=len(modified_access),
                removed=len(removed_access),
            )
            res["partners"] = partners
        if self.access_internal.startswith(self.WRITE_VALUE_PREFIX):
            res["access_internal"] = self.access_internal.removeprefix(
                self.WRITE_VALUE_PREFIX
            )
        if self.access_via_link.startswith(self.WRITE_VALUE_PREFIX):
            res["access_via_link"] = self.access_via_link.removeprefix(
                self.WRITE_VALUE_PREFIX
            )
        if self.access_via_link_mode.startswith(self.WRITE_VALUE_PREFIX):
            res["is_access_via_link_hidden"] = (
                self.access_via_link_mode == f"{self.WRITE_VALUE_PREFIX}link_required"
            )
        if self.viewer_download_mode.startswith(self.WRITE_VALUE_PREFIX):
            res["is_download_blocked"] = (
                self.viewer_download_mode == f"{self.WRITE_VALUE_PREFIX}blocked"
            )
        return res
