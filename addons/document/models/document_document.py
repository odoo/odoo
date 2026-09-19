import base64
import contextlib
import io
import logging
import re
import string
import uuid
from collections import defaultdict
from typing import Any, NamedTuple
from urllib.parse import quote
from urllib.parse import urlencode as url_encode

from dateutil.relativedelta import relativedelta

import odoo
from odoo import SUPERUSER_ID, Command, _, api, fields, models, modules
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import get_extension
from odoo.tools import SQL, groupby
from odoo.tools.date_utils import time_unit_selection
from odoo.tools.image import image_process
from odoo.tools.misc import clean_context
from odoo.tools.pdf import PdfReader

from odoo.addons.document.tools import UserFolder
from odoo.addons.mail.tools import link_preview

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _normalize_file_extension(extension: str) -> str:
    return re.sub(r"^[\s.]+|\s+$", "", extension)


class DocumentMovePlan(NamedTuple):
    """What a `folder_id` change decided, carried across `super().write`.

    The move is validated before the ORM write and acted on after it, and
    everything it needs -- which documents actually change folder, and which
    folder each one came from -- stops being readable the moment the write
    lands. `resolved_vals` is the one non-empty case: the destination was a
    shortcut, so nothing was planned and the caller restarts against the
    target.
    """

    new_parent_folder: Any
    documents_to_move: Any
    documents_to_move_per_initial_folder: dict
    resolved_vals: dict | None


class DocumentsDocument(models.Model):
    _name = "document.document"
    _description = "Document"
    _inherit = [
        "mixin.mail.thread.cc",
        "mixin.mail.activity",
        "mixin.mail.alias.optional",
        "mixin.user.favorite",
    ]
    _mail_post_access = "read"
    _order = "sequence, id desc"
    _parent_name = "folder_id"
    _parent_store = True
    _systray_view = "activity"

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index="btree_not_null",
        tracking=True,
    )
    owner_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user.id if self.env.user.active else False,
        index=True,
        copy=False,
        tracking=True,
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        copy=False,
        ondelete="cascade",
        bypass_search_access=True,
    )
    attachment_name = fields.Char(
        related="attachment_id.name",
        string="Attachment Name",
        readonly=False,
    )
    description = fields.Text(
        related="attachment_id.description",
        string="Attachment Description",
        readonly=False,
    )
    attachment_type = fields.Selection(
        related="attachment_id.type",
        string="Attachment Type",
        readonly=False,
    )
    checksum = fields.Char(related="attachment_id.checksum")
    mimetype = fields.Char(related="attachment_id.mimetype")
    index_content = fields.Text(related="attachment_id.index_content")
    raw = fields.Binary(
        related="attachment_id.raw",
        related_sudo=True,
        readonly=False,
        prefetch=False,
    )
    datas = fields.Binary(
        related="attachment_id.datas",
        related_sudo=True,
        readonly=False,
        prefetch=False,
    )

    shortcut_document_id = fields.Many2one(
        comodel_name="document.document",
        string="Source Document",
        index="btree_not_null",
        ondelete="cascade",
    )
    shortcut_document_owner_id = fields.Many2one(
        comodel_name="res.users",
        related="shortcut_document_id.owner_id",
        string="Source Document Owner",
    )
    shortcut_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="shortcut_document_id",
    )

    file_size = fields.Integer(
        compute="_compute_file_size",
        store=True,
    )
    res_model = fields.Char(
        string="Resource Model",
        compute="_compute_res_record",
        inverse="_inverse_res_record",
        recursive=True,
        store=True,
    )
    res_model_name = fields.Char(compute="_compute_res_model_name")
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Resource ID",
        compute="_compute_res_record",
        inverse="_inverse_res_record",
        recursive=True,
        store=True,
    )
    res_name = fields.Char(
        string="Resource Name",
        compute="_compute_res_name",
    )

    previous_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="History",
        bypass_search_access=True,
    )

    name = fields.Char(
        translate=True,
        compute="_compute_name_and_preview",
        recursive=True,
        store=True,
        copy=True,
        readonly=False,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    type = fields.Selection(
        selection=[("url", "URL"), ("binary", "File"), ("folder", "Folder")],
        default="binary",
        index=True,
        readonly=True,
        required=True,
    )
    is_folder = fields.Boolean(
        compute="_compute_is_folder",
        order_by_sql="_order_by_sql_is_folder",
    )
    thumbnail = fields.Binary(
        attachment=True,
        compute="_compute_thumbnail",
        recursive=True,
        store=True,
        readonly=False,
    )
    thumbnail_status = fields.Selection(
        selection=[
            ("present", "Present"),
            ("error", "Error"),
            (
                "client_generated",
                "Client Generated",
            ),
        ],
        compute="_compute_thumbnail",
        recursive=True,
        store=True,
        readonly=False,
    )
    url = fields.Char(
        string="Link URL",
        size=1024,
        index=True,
        tracking=True,
    )
    url_preview_image = fields.Char(
        string="URL Preview Image",
        compute="_compute_name_and_preview",
        recursive=True,
        store=True,
        readonly=False,
    )
    url_preview_pending = fields.Boolean(
        string="URL preview to fetch",
        default=False,
        copy=False,
        help="Set when a URL document still needs its link preview fetched "
        "asynchronously (see _cron_update_url_preview).",
    )
    request_activity_id = fields.Many2one(comodel_name="mail.activity")
    requestee_partner_id = fields.Many2one(comodel_name="res.partner")
    tag_ids = fields.Many2many(
        comodel_name="document.tag",
        relation="document_tag_rel",
        string="Tags",
    )
    lock_uid = fields.Many2one(
        comodel_name="res.users",
        string="Locked by",
        tracking=True,
    )

    document_token = fields.Char(
        default=lambda __: (
            base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().removesuffix("==")
        ),
        copy=False,
        required=True,
    )
    access_token = fields.Char(compute="_compute_access_token")

    access_url = fields.Char(
        string="Access url",
        compute="_compute_access_url",
    )
    is_access_via_link_hidden = fields.Boolean(
        string="Link Access Hidden",
        index=True,
        help='If "True", only people given direct access to this document will be able to view it. '
        'If "False", access with the link also given to all who can access the parent folder.',
    )
    access_via_link = fields.Selection(
        selection=[("view", "Viewer"), ("edit", "Editor"), ("none", "None")],
        string="Link Access Rights",
        default="none",
        index=True,
        required=True,
    )
    is_download_blocked = fields.Boolean(
        string="Block Download",
        default=False,
        help="If set, people who can only view this document cannot download "
        "it. Editors are unaffected: they can replace the content, so "
        "withholding it from them would mean nothing.",
    )
    access_internal = fields.Selection(
        selection=[("view", "Viewer"), ("edit", "Editor"), ("none", "None")],
        string="Internal Users Rights",
        default="none",
        index=True,
        required=True,
    )

    access_ids = fields.One2many(
        comodel_name="document.access",
        inverse_name="document_id",
        string="Allowed Access",
    )

    user_permission = fields.Selection(
        selection=[("edit", "Editor"), ("view", "Viewer"), ("none", "None")],
        string="User permission",
        compute="_compute_user_permission",
        search="_search_user_permission",
        compute_sudo=True,
    )
    user_can_move = fields.Boolean(
        string="Can move it",
        compute="_compute_user_can_move",
    )

    parent_path = fields.Char(index=True)
    folder_id = fields.Many2one(
        comodel_name="document.document",
        search="_search_folder_id",
        index=True,
        required=False,
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]",
        ondelete="set null",
        tracking=True,
    )
    user_folder_id = fields.Char(
        string="Parent",
        compute="_compute_user_folder_id",
        search="_search_user_folder_id",
        compute_sudo=True,
    )
    children_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="folder_id",
    )

    deletion_delay = fields.Integer(
        string="Deletion delay",
        compute="_compute_deletion_delay",
        help="Delay after permanent deletion of the document in the trash (days)",
    )
    deletion_date = fields.Date(
        string="Deletion Date",
        index="btree_not_null",
        copy=False,
        help="When this document, sitting in the trash, is deleted forever. "
        "Set when it is sent to the trash and cleared when it is restored.",
    )

    create_activity_option = fields.Boolean(
        string="Create a new activity",
        compute="_compute_create_activity_option",
        store=True,
        readonly=False,
    )
    create_activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity type",
    )
    create_activity_summary = fields.Char(string="Summary")
    create_activity_date_deadline_range = fields.Integer(string="Due Date In")
    create_activity_date_deadline_range_type = fields.Selection(
        selection=time_unit_selection("day", "week", "month"),
        string="Due type",
        default="day",
    )
    create_activity_note = fields.Html(string="Note")
    create_activity_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
    )

    available_embedded_actions_ids = fields.Many2many(
        comodel_name="ir.embedded.actions",
        string="Available Actions",
        compute="_compute_available_embedded_actions_ids",
        groups="base.group_user",
    )

    alias_tag_ids = fields.Many2many(
        comodel_name="document.tag",
        relation="document_alias_tag_rel",
        string="Alias Tags",
    )
    mail_alias_domain_count = fields.Integer(compute="_compute_mail_alias_domain_count")

    is_editable_attachment = fields.Boolean(
        default=False,
        help="True if we can edit the link attachment.",
    )
    is_multipage = fields.Boolean(
        string="Is considered multipage",
        compute="_compute_is_multipage",
        store=True,
        readonly=False,
    )
    file_extension = fields.Char(
        compute="_compute_file_extension",
        inverse="_inverse_file_extension",
        store=True,
        copy=True,
        readonly=False,
    )

    last_access_date_group = fields.Selection(
        selection=[
            ("0_older", "Older"),
            ("1_month", "This Month"),
            ("2_week", "This Week"),
            ("3_day", "Today"),
        ],
        string="Last Accessed On",
        compute="_compute_last_access_date_group",
        search="_search_last_access_date_group",
        order_by_sql="_order_by_sql_last_access_date_group",
        value_sql="_last_access_date_group_sql",
    )

    _res_model_res_id_idx = models.Index("(res_model, res_id)")

    _attachment_unique = models.Constraint(
        "unique (attachment_id)",
        "This attachment is already a document",
    )
    _document_token_unique = models.Constraint(
        "unique (document_token)",
        "Access tokens already used.",
    )
    _folder_id_not_id = models.Constraint(
        "check(folder_id <> id)",
        "A folder cannot be included in itself",
    )
    _shortcut_document_id_not_id = models.Constraint(
        "check(shortcut_document_id <> id)",
        "A shortcut cannot point to itself",
    )

    @api.constrains("document_token")
    def _check_document_token(self) -> None:
        charset = set(string.ascii_letters + string.digits + "-_")
        for document in self:
            if (
                len(document.document_token or "") != 22
                or set(document.document_token) - charset
            ):
                raise ValidationError(_("Invalid document token"))

    @api.constrains(
        "shortcut_document_id",
        "shortcut_ids",
        "type",
        "folder_id",
        "children_ids",
        "company_id",
    )
    def _check_shortcut_fields(self) -> None:
        errors = []
        wrong_types, wrong_companies = self.browse(), self.browse()
        chained_shortcuts = self.browse()
        wrong_parents_sudo = self.folder_id.sudo().filtered("shortcut_document_id")
        for target in self.filtered("shortcut_ids"):
            for shortcut in target.shortcut_ids:
                if shortcut.type != target.type:
                    wrong_types |= shortcut
        for shortcut in self.filtered("shortcut_document_id"):
            if shortcut.type != shortcut.shortcut_document_id.type:
                wrong_types |= shortcut
            if shortcut.children_ids:
                wrong_parents_sudo |= shortcut
            if shortcut.shortcut_document_id.sudo().shortcut_document_id:
                chained_shortcuts |= shortcut
            if (
                shortcut.shortcut_document_id.company_id
                and shortcut.shortcut_document_id.company_id != shortcut.company_id
            ):
                wrong_companies |= shortcut
        if wrong_types:
            message = _("The following documents/shortcuts have a type mismatch: \n")
            documents_list = "\n- ".join(wrong_types.mapped("name"))
            errors.append(f"{message}\n- {documents_list}")
        if wrong_parents_sudo:
            message = _(
                "The following shortcuts cannot be set as documents parents: \n"
            )
            shortcuts_list = "\n- ".join(wrong_parents_sudo.mapped("name"))
            errors.append(f"{message}\n- {shortcuts_list}")
        if wrong_companies:
            message = _("The following documents/shortcuts have a company mismatch: \n")
            shortcuts_list = "\n- ".join(wrong_companies.mapped("name"))
            errors.append(f"{message}\n- {shortcuts_list}")
        if chained_shortcuts:
            message = _(
                "The following shortcuts point at another shortcut instead of a "
                "document: \n"
            )
            shortcuts_list = "\n- ".join(chained_shortcuts.mapped("name"))
            errors.append(f"{message}\n- {shortcuts_list}")
        if errors:
            _debug.logic(
                "shortcut_constraint_refused",
                documents=self,
                wrong_types=len(wrong_types),
                wrong_parents=len(wrong_parents_sudo),
                wrong_companies=len(wrong_companies),
                chained=len(chained_shortcuts),
            )
            raise ValidationError("\n\n".join(errors))

    @api.constrains("owner_id", "folder_id")
    def _check_root_documents_owner_id(self) -> None:
        root_documents = self.filtered(lambda d: not d.folder_id)
        unauthorized_owners_sudo = (
            root_documents._get_unauthorized_root_document_owners_sudo()
        )
        if unauthorized_owners_sudo:
            _debug.logic(
                "root_owner_refused",
                documents=root_documents,
                owners=unauthorized_owners_sudo,
            )
            users_documents_list = [
                (document.owner_id.name, document.name)
                for document in root_documents
                if document.owner_id in unauthorized_owners_sudo
            ]
            raise ValidationError(
                _(
                    "The following user(s) cannot own root documents/folders: \n- %(lines)s",
                    lines="\n-".join(
                        f"{user_name}: {doc_name}"
                        for user_name, doc_name in users_documents_list
                    ),
                )
            )

    @api.constrains("res_model")
    def _check_res_model(self) -> None:
        # Read the value off the recordset rather than asking the database for
        # it. The `search_count` this replaces went through `_search`, which
        # applies `active_test` -- so the rule simply did not exist for an
        # archived document. Archive, link, restore, and an ACTIVE document
        # linked to another document (or to ITSELF, `res_id == id`) was left
        # behind, which is the exact state this constraint is here to forbid.
        # It also cost a flush and a round-trip per `create` for values already
        # in memory.
        offenders = self.filtered(lambda d: d.res_model == "document.document")
        if offenders:
            _debug.logic("res_model_refused", documents=offenders)
            raise ValidationError(
                _(
                    "A document can not be linked to itself or another "
                    "document: %(documents)s",
                    documents=", ".join(offenders.mapped("name")),
                )
            )

    @api.constrains("url")
    def _check_url(self) -> None:
        for document in self.filtered("url"):
            if not document.url.startswith(("https://", "http://", "ftp://")):
                raise ValidationError(
                    _(
                        "URL %s does not seem complete, as it does not begin with http(s):// or ftp://",
                        document.url,
                    )
                )

    def _pop_attachment_vals(self, vals: dict) -> dict:
        keys = [
            key
            for key in list(vals)
            if (field := self._fields.get(key)) is not None
            and field.related
            and field.related.split(".")[0] == "attachment_id"
        ]
        return {key: vals.pop(key) for key in keys}

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> DocumentsDocument:
        _debug.pipeline("create_start", count=len(vals_list), su=self.env.su)
        attachments = []
        for vals in vals_list:
            self._clean_vals_for_user_folder_id(vals, is_create=True)
        self._check_parent_folders([vals.get("folder_id") for vals in vals_list])
        # The attachments a vals carries its content in are created in ONE call
        # for the whole batch, not one call per document: `ir.attachment.create`
        # is a row insert plus its own filestore work, so doing it per vals made
        # creating N documents cost N inserts where the documents themselves
        # cost one. Collected here, created below.
        pending_attachment_vals = {}
        for position, vals in enumerate(vals_list):
            attachment_dict = self._pop_attachment_vals(vals)
            attachment = self.env["ir.attachment"].browse(vals.get("attachment_id"))
            if not self.env.su and self.env.user.share:
                if not vals.get("folder_id"):
                    _debug.logic("create_refused", reason="share_user_no_folder")
                    raise AccessError(
                        _("You are not allowed to create documents here.")
                    )
                for access_field in ("access_internal", "access_via_link"):
                    vals.pop(access_field, None)
            if attachment and attachment_dict:
                attachment.write(attachment_dict)
            elif attachment_dict:
                attachment_dict.setdefault("name", vals.get("name", "unnamed"))
                pending_attachment_vals[position] = attachment_dict
            attachments.append(attachment)

        if pending_attachment_vals:
            _debug.lifecycle(
                "attachment_created_for_document", count=len(pending_attachment_vals)
            )
            created_attachments = (
                self.env["ir.attachment"]
                .with_context(clean_context(self.env.context))
                .create(list(pending_attachment_vals.values()))
            )
            for position, attachment in zip(
                pending_attachment_vals, created_attachments, strict=True
            ):
                vals_list[position]["attachment_id"] = attachment.id
                attachments[position] = attachment

        for vals, attachment in zip(vals_list, attachments, strict=True):
            if attachment and not vals.get("name"):
                vals["name"] = attachment.name

        with _debug.perf("create_super", cr=self.env.cr, count=len(vals_list)):
            documents = super(
                DocumentsDocument, self.with_context(default_access_ids=None)
            ).create(vals_list)

        if not self._is_documents_manager():
            if any(d.alias_name for d in documents):
                _debug.logic("create_refused", reason="alias_needs_manager")
                raise AccessError(_("Only Documents Managers can set aliases."))
            if any(d._is_company_root_folder() for d in documents):
                _debug.logic("create_refused", reason="company_root_needs_manager")
                self._raise_company_folder_manager_only()

        for document, attachment in zip(documents, attachments, strict=True):
            if (
                attachment
                and not attachment.res_id
                and (
                    not attachment.res_model
                    or attachment.res_model == "document.document"
                )
            ):
                attachment.with_context(no_document=True).write(
                    {
                        "res_model": "document.document",
                        "res_id": document.id,
                    }
                )
        # A document can be BORN in the trash -- `message_new` creates every
        # mail-gateway document with `active=False`, and `document_sign` does
        # the same for its signed copies. `_write_check_active_after` never
        # runs for those, so without this they would carry no deletion date and
        # `_gc_clear_bin`, which purges on that date, would leave them in the
        # trash for good. The invariant is "not active implies a deletion
        # date", and it is owned by the two places `active` can take that
        # value: here and on the write transition.
        if born_archived := documents.filtered(
            lambda document: not document.active and not document.deletion_date
        ):
            born_archived.sudo().deletion_date = self._next_deletion_date()

        self._mark_url_preview_pending(documents)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                documents=documents,
                types=sorted({d.type or "" for d in documents}),
            )
        return documents

    @api.model
    def _shortcut_access_defaults(self, target: DocumentsDocument) -> dict:
        return {
            "access_internal": target.access_internal or "view",
            "access_via_link": target.access_via_link or "none",
        }

    @api.model
    def _trigger_url_preview_cron(self) -> None:
        cron = self.env.ref("document.ir_cron_url_preview", raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()

    def _locked_by_other(self) -> DocumentsDocument:
        if self.env.su or self._is_documents_manager():
            return self.browse()
        return self.filtered(lambda d: d.lock_uid and d.lock_uid != self.env.user)

    @api.model
    def _check_parent_folders(self, folder_ids: list) -> None:
        folders = self.browse({folder_id for folder_id in folder_ids if folder_id})
        if folders and folders.sudo().filtered(lambda folder: folder.type != "folder"):
            _debug.logic(
                "parent_folder_refused", reason="not_a_folder", folders=folders
            )
            raise UserError(_("Invalid folder id"))

    def write(self, vals: dict) -> bool:
        """Apply `vals`, running the document-specific steps around the ORM write.

        The steps are ordered and several of them look at state that the ORM
        write itself destroys, so each one says in its name whether it runs
        BEFORE or AFTER `super().write`. They are methods rather than blocks so
        that a bridge module can extend one of them instead of this whole
        sequence, and so each is reachable from a test on its own.
        """
        _debug.lifecycle("write", documents=self, fields=sorted(vals))
        if "shortcut_document_id" in vals:
            _debug.logic("write_refused", reason="shortcut_retarget", documents=self)
            raise UserError(_("Shortcuts cannot change target document."))

        if (
            vals.get("active") is False
            and not self.env.su
            and not self.env.context.get("documents_archiving")
        ):
            _debug.pipeline("write_rerouted_to_archive", documents=self)
            if remaining_vals := {k: v for k, v in vals.items() if k != "active"}:
                self.write(remaining_vals)
            self.action_archive()
            return True

        self._clean_vals_for_user_folder_id(vals)

        is_manager = self._is_documents_manager()
        pinned_folders_start = self.filtered(lambda d: d._is_company_root_folder())

        writes_content, has_content = self._write_content_flags(vals)
        self._write_check_lock_before(vals, writes_content)
        previous_owner_access_to_keep = self._write_check_owner_before(vals, is_manager)

        move = self._write_plan_move_before(vals)
        if move.resolved_vals is not None:
            # The destination is a shortcut: retry against what it points at.
            return self.write(move.resolved_vals)

        documents_per_initial_active = self._write_check_active_before(vals)

        if vals.get("attachment_id"):
            self.check_singleton()
        attachments_was_present, versioned = self._write_apply_versioning_before(
            vals, writes_content, has_content
        )

        attachment_dict = self._pop_attachment_vals(vals)

        if not is_manager and set(vals) & set(self.env["mixin.mail.alias"]._fields):
            _debug.logic("write_refused", reason="alias_needs_manager")
            raise AccessError(_("Only Documents Managers can set aliases."))

        with _debug.perf("write_super", cr=self.env.cr, documents=self):
            write_result = super().write(vals)
        if attachment_dict:
            self.attachment_id.write(attachment_dict)

        if "attachment_id" in vals:
            self.attachment_id.check_access("read")

        versioned._remove_excess_versions()

        self._write_check_active_after(vals, documents_per_initial_active)

        if (
            not is_manager
            and self.filtered(lambda d: d._is_company_root_folder())
            != pinned_folders_start
        ):
            self._raise_company_folder_manager_only()

        self._write_fulfil_requests_after(attachments_was_present)

        if (
            (company_id := vals.get("company_id")) is not None
        ) and self.shortcut_ids | self.children_ids:
            self._update_company(company_id)

        self._add_user_role_without_propagation("edit", previous_owner_access_to_keep)

        self._write_sync_moved_after(vals, move)

        if "url" in vals:
            self._mark_url_preview_pending(self)

        _debug.pipeline(
            "write_done",
            documents=self,
            moved=len(move.documents_to_move),
            versioned=len(versioned),
        )
        return write_result

    @api.model
    def _write_content_flags(self, vals: dict) -> tuple[bool, bool]:
        content_keys = ("datas", "raw")
        return (
            any(key in vals for key in content_keys),
            any(vals.get(key) for key in content_keys),
        )

    def _write_check_lock_before(self, vals: dict, writes_content: bool) -> None:
        replaces_content = writes_content or "attachment_id" in vals
        if replaces_content and (locked_by_other := self._locked_by_other()):
            _debug.logic("write_refused", reason="locked_by_other")
            raise UserError(
                _(
                    "“%(name)s” is locked by %(user)s and its content cannot "
                    "be replaced by another user.",
                    name=locked_by_other[0].name,
                    user=locked_by_other[0].lock_uid.name,
                )
            )

    def _write_check_owner_before(self, vals: dict, is_manager: bool) -> dict:
        """Refuse an owner change on documents this user does not own.

        Returns the documents whose owner is about to change, grouped by their
        CURRENT owner -- read here because `super().write` overwrites it, and
        needed afterwards to leave that owner an explicit `edit` membership.
        """
        if (owner_id := vals.get("owner_id")) is None:
            return {}
        if not is_manager and any(d.owner_id != self.env.user for d in self):
            _debug.logic("write_refused", reason="owner_change_not_owner")
            raise AccessError(
                _("You cannot change the owner of documents you do not own.")
            )
        if not isinstance(owner_id, int | bool | None):
            owner_id = owner_id.id
        documents_changing_owner = self.filtered(
            lambda d: d.owner_id and d.owner_id.id != owner_id
        )
        _debug.logic("owner_changed", documents=documents_changing_owner, to=owner_id)
        return dict(documents_changing_owner.grouped("owner_id"))

    def _write_plan_move_before(self, vals: dict) -> DocumentMovePlan:
        """Validate a `folder_id` change and capture what the move needs later.

        `resolved_vals` set on the result means the destination turned out to be
        a shortcut and the caller must restart against the target instead; every
        other field is empty in that case.
        """
        empty = self.browse()
        if "folder_id" not in vals:
            return DocumentMovePlan(empty, empty, {}, None)

        self._check_parent_folders([vals["folder_id"]])
        new_parent_folder = self.browse(vals["folder_id"])
        documents_to_move = self.filtered(lambda d: d.folder_id != new_parent_folder)
        if documents_to_move and new_parent_folder and not new_parent_folder.active:
            _debug.logic("move_refused", reason="target_archived")
            raise UserError(
                _("It is not possible to move documents into archived folders.")
            )
        if documents_to_move and not self.env.su:
            self._write_check_move_access(documents_to_move, new_parent_folder)

        if new_parent_folder.shortcut_document_id:
            _debug.pipeline(
                "move_target_resolved_through_shortcut",
                shortcut=new_parent_folder,
                target=new_parent_folder.shortcut_document_id,
            )
            resolved_vals = vals | {
                "folder_id": new_parent_folder.shortcut_document_id.id
            }
            resolved_vals.pop("user_folder_id", None)
            return DocumentMovePlan(empty, empty, {}, resolved_vals)

        if new_parent_folder:
            self._write_check_move_not_archived(documents_to_move, vals)

        documents_to_move_per_initial_folder = documents_to_move.grouped("folder_id")
        _debug.pipeline(
            "move_planned",
            documents=documents_to_move,
            to=new_parent_folder,
            from_folders=len(documents_to_move_per_initial_folder),
        )
        return DocumentMovePlan(
            new_parent_folder,
            documents_to_move,
            dict(documents_to_move_per_initial_folder),
            None,
        )

    def _write_check_move_access(
        self, documents_to_move: DocumentsDocument, new_parent_folder: DocumentsDocument
    ) -> None:
        if new_parent_folder and new_parent_folder.user_permission != "edit":
            _debug.logic("move_refused", reason="target_not_editable")
            raise AccessError(_("You can't access that folder_id."))
        for doc in documents_to_move:
            if doc.user_permission != "edit":
                _debug.logic("move_refused", reason="source_not_editable")
                raise AccessError(
                    _("You are not allowed to move (some of) these documents.")
                )
            if not doc.user_can_move:
                _debug.logic("move_refused", reason="cannot_move_out")
                raise AccessError(
                    _(
                        "You can't move documents you do not own out of folders you cannot edit."
                    )
                )

    def _write_check_move_not_archived(
        self, documents_to_move: DocumentsDocument, vals: dict
    ) -> None:
        for doc in documents_to_move:
            to_active = vals.get("active")
            if (not doc.active and not to_active) or (
                doc.folder_id
                and not doc.folder_id.active
                and (not to_active or doc.folder_id not in self)
            ):
                _debug.logic("move_refused", reason="source_archived")
                raise UserError(_("It is not possible to move archived documents."))

    def _write_check_active_before(self, vals: dict) -> dict:
        if (to_active := vals.get("active")) is None:
            return {}
        if to_active is False:
            if not self.env.su and self.env.user.share:
                _debug.logic("archive_refused", reason="share_user", documents=self)
                raise UserError(_("You are not allowed to (un)archive documents."))
            self.check_access("unlink")
        return dict(self.grouped("active"))

    def _write_apply_versioning_before(
        self, vals: dict, writes_content: bool, has_content: bool
    ) -> tuple[list[bool], DocumentsDocument]:
        """Move the outgoing content into the version history.

        Returns which records already held an attachment -- read before the
        write, and the only way to tell afterwards that a document request was
        just fulfilled -- and the records that gained a version.
        """
        attachment_id = vals.get("attachment_id")
        attachments_was_present = []
        versioned = self.browse()
        replaced_content = self.browse()
        for record in self:
            attachments_was_present.append(bool(record.attachment_id))
            fulfils_request = (
                record.request_activity_id
                and not record.attachment_id
                and (has_content or attachment_id)
            )
            if (
                record.type == "binary"
                and (writes_content or "url" in vals)
                and (not record.attachment_id or not record.attachment_id.file_size)
                and not fulfils_request
            ):
                record.with_context(no_document=True).message_post(
                    body=_(
                        "Document Request: %(name)s Uploaded by: %(user)s",
                        name=record.name,
                        user=self.env.user.name,
                    )
                )

            if record.attachment_id:
                outcome = self._write_version_existing(record, vals, writes_content)
                if outcome:
                    versioned |= record
                if outcome == "content_copy":
                    replaced_content |= record
            elif has_content and not attachment_id:
                self._write_attach_empty_document(record, vals)

        # One `copy()` for every record whose content is being overwritten:
        # `copy()` ends in a single `create()`, so calling it per record turned
        # N version snapshots into N inserts.
        self._write_snapshot_replaced_content(replaced_content)
        return attachments_was_present, versioned

    def _write_snapshot_replaced_content(self, records: DocumentsDocument) -> None:
        if not records:
            return
        snapshots = records.attachment_id.with_context(no_document=True).copy()
        for record, snapshot in zip(records, snapshots, strict=True):
            # `copy()` already carries the source's res_model/res_id, which for
            # a document-owned file is this document -- so only a file that
            # lives on another record needs redirecting, and the common case
            # writes nothing.
            if (snapshot.res_model, snapshot.res_id) != (
                "document.document",
                record.id,
            ):
                snapshot.write({"res_model": "document.document", "res_id": record.id})
            record.previous_attachment_ids = [(4, snapshot.id, False)]
            _debug.logic("versioned", by="content_copy", document=record)

    def _write_version_existing(
        self, record: DocumentsDocument, vals: dict, writes_content: bool
    ) -> str | bool:
        """Report which kind of version this write creates, if any.

        A content overwrite is only REPORTED here ("content_copy") and carried
        out by `_write_snapshot_replaced_content` for the whole batch at once;
        the other two shapes are per-record by nature and rare.
        """
        attachment_id = vals.get("attachment_id")
        if attachment_id and attachment_id != record.attachment_id.id:
            attachment = self.env["ir.attachment"].browse(attachment_id)
            if (attachment.res_model, attachment.res_id) != (
                record.res_model,
                record.res_id,
            ):
                res_model, res_id = record._owning_record_link()
                attachment.with_context(no_document=True).write(
                    {"res_model": res_model, "res_id": res_id}
                )

            related_record = record.res_model in self.env and self.env[
                record.res_model
            ].browse(record.res_id)
            if (
                not hasattr(related_record, "message_main_attachment_id")
                or related_record.message_main_attachment_id != record.attachment_id
            ):
                record.attachment_id.with_context(no_document=True).write(
                    {"res_model": "document.document", "res_id": record.id}
                )
            if attachment_id in record.previous_attachment_ids.ids:
                record.previous_attachment_ids = [(3, attachment_id, False)]
            record.previous_attachment_ids = [(4, record.attachment_id.id, False)]
            _debug.logic("versioned", by="attachment_swap", document=record)
            return "swap"
        if "attachment_id" in vals and not attachment_id:
            # Detaching the file outright. This used to keep no version
            # at all: the document went empty, the outgoing attachment
            # stayed behind pointing at it, and the history panel
            # offered nothing to go back to -- unlike every other way of
            # replacing the content. Emptying a document IS replacing
            # its content, which is how the lock guard above already
            # reads it.
            #
            # The attachment itself becomes the previous version, not a
            # copy of it: nothing is overwriting it here, so the copy
            # the branch below makes would archive a duplicate and leave
            # the original dangling.
            record.previous_attachment_ids = [(4, record.attachment_id.id, False)]
            _debug.logic("versioned", by="detach", document=record)
            return "detach"
        if writes_content:
            return "content_copy"
        return False

    def _write_attach_empty_document(
        self, record: DocumentsDocument, vals: dict
    ) -> None:
        res_model = vals.get("res_model", record.res_model)
        res_id = vals.get("res_id", record.res_id)
        if res_model and (
            res_model not in self.env or not self.env[res_model].browse(res_id).exists()
        ):
            # A model the registry no longer has is the strongest form of "the
            # linked record is gone", which is what this branch is already for.
            # It used to index `self.env[res_model]` first and raise KeyError.
            _debug.logic(
                "res_record_cleared",
                res_model=res_model,
                reason="model" if res_model not in self.env else "record",
            )
            record.res_model = False
            record.res_id = False

        owning_model, owning_id = record._owning_record_link()
        record.attachment_id = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create(
                {
                    "name": vals.get("name", record.name),
                    "res_model": owning_model,
                    "res_id": owning_id,
                }
            )
            .id
        )

    @api.model
    def _next_deletion_date(self):
        return fields.Date.today() + relativedelta(days=self.get_deletion_delay())

    def _write_check_active_after(
        self, vals: dict, documents_per_initial_active: dict
    ) -> None:
        if (new_active := vals.get("active")) is None:
            return
        # Stamp on the TRANSITION, not in `action_archive`. `write` reroutes a
        # bare `active=False` to `action_archive` only when the caller is not
        # superuser, so `doc.sudo().write({"active": False})` -- which several
        # bridges do -- reached the trash with no deletion date, and a purge
        # that reads that date would have left those documents in the trash for
        # good. Here every path that flips `active` is covered, including the
        # one `action_archive` itself takes.
        if not new_active:
            if newly_archived := documents_per_initial_active.get(True):
                newly_archived.sudo().deletion_date = self._next_deletion_date()
        elif restored := documents_per_initial_active.get(False):
            restored.sudo().deletion_date = False
        if not new_active:
            if self.sudo().search(
                [("id", "child_of", self.ids), ("active", "=", True)]
            ):
                _debug.logic("archive_refused", reason="active_descendants")
                raise UserError(
                    _(
                        'Operation not supported. Please use "Move to Trash" / `action_archive` instead.'
                    )
                )
            if archived_documents := documents_per_initial_active.get(True):
                archived_documents._log_transition_to_parent_folders(
                    lambda names: self.env._(
                        "The following documents have been sent to trash: "
                        "%(documents)s.",
                        documents=names,
                    )
                )
        else:
            if self.sudo().search(
                [("id", "parent_of", self.ids), ("active", "=", False)]
            ):
                _debug.logic("unarchive_refused", reason="archived_ancestors")
                raise UserError(
                    _(
                        'Operation not supported. Please use "Restore" / `action_unarchive` instead.'
                    )
                )
            if restored_documents := documents_per_initial_active.get(False):
                restored_documents._log_transition_to_parent_folders(
                    lambda names: self.env._(
                        "The following documents have been restored from the "
                        "trash: %(documents)s.",
                        documents=names,
                    )
                )

    def _write_fulfil_requests_after(self, attachments_was_present: list[bool]) -> None:
        for document, attachment_was_present in zip(
            self, attachments_was_present, strict=True
        ):
            if (
                document.request_activity_id
                and document.attachment_id
                and not attachment_was_present
            ):
                feedback = _(
                    "Document Request: %(name)s Uploaded by: %(user)s",
                    name=document.name,
                    user=self.env.user.name,
                )
                document.with_context(
                    no_document=True
                ).request_activity_id.action_feedback(
                    feedback=feedback, attachment_ids=[document.attachment_id.id]
                )

    def _write_sync_moved_after(self, vals: dict, move: DocumentMovePlan) -> None:
        if move.new_parent_folder and (
            documents_to_sync := move.documents_to_move.filtered(
                lambda d: not d.shortcut_document_id
            )
        ):
            _debug.pipeline(
                "move_access_synced",
                documents=documents_to_sync,
                folder=move.new_parent_folder,
                access_internal=move.new_parent_folder.access_internal,
                access_via_link=move.new_parent_folder.access_via_link,
            )
            documents_to_sync.action_update_access_rights(
                access_internal=move.new_parent_folder.access_internal,
                access_via_link=move.new_parent_folder.access_via_link,
                partners={
                    access.partner_id: (access.role, access.expiration_date)
                    for access in move.new_parent_folder.access_ids
                    if access.role
                },
            )
            if "company_id" not in vals:
                documents_to_sync._update_company(move.new_parent_folder.company_id.id)

        if not move.documents_to_move:
            return
        for folder, documents in move.documents_to_move.grouped("folder_id").items():
            if folder:
                folder.message_post_with_source(
                    source_ref="document.folder_notification_move_in",
                    render_values={"documents": documents},
                )
        for folder, documents in move.documents_to_move_per_initial_folder.items():
            if folder:
                folder.message_post_with_source(
                    source_ref="document.folder_notification_move_out",
                    render_values={"documents": documents},
                )

    def copy(self, default: dict | None = None) -> DocumentsDocument:
        if not self:
            return self
        if not all(self.mapped("active")):
            _debug.logic("copy_refused", reason="in_trash", documents=self)
            raise UserError(_("You cannot duplicate document(s) in the Trash."))
        if default and default.get("user_folder_id") == UserFolder.MY:
            default["owner_id"] = self.env.user.id

        self.env["document.document"].check_access("create")
        self.check_access("read")
        documents_order = {doc.id: idx for idx, doc in enumerate(self)}
        new_documents = [self.browse()] * len(self)
        is_manager = self._is_documents_manager()
        skip_documents = self.env.context.get("documents_copy_folders_only")

        shortcuts = self.filtered("shortcut_document_id")
        _debug.pipeline(
            "copy_start",
            documents=self,
            shortcuts=len(shortcuts),
            folders_only=bool(skip_documents),
        )
        if shortcuts and not skip_documents:
            for destination, targets in self._get_copy_shortcuts_destinations(
                shortcuts, default
            ):
                new_shortcuts = targets.action_create_shortcut(
                    location_user_folder_id=destination
                )
                for new_shortcut, target in zip(new_shortcuts, targets, strict=True):
                    new_shortcut.name = _("%s (copy)", target.name)
                    new_documents[documents_order[target.id]] = new_shortcut

        folders = (self - shortcuts).filtered(lambda d: d.type == "folder")
        if folders:
            if (
                not is_manager
                and default
                and default.get("user_folder_id") == UserFolder.COMPANY
            ):
                self._raise_company_folder_manager_only()

            embedded_actions = self._get_folder_embedded_actions(folders.ids)
            new_folders = folders.sudo()._copy_with_access(default=default).sudo(False)

            self.browse(
                [
                    new_folder.id
                    for old_folder, new_folder in zip(folders, new_folders, strict=True)
                    if old_folder._cannot_create_sibling()
                ]
            ).sudo().write({"folder_id": False})

            for old_folder, new_folder in zip(folders, new_folders, strict=True):
                if folder_embedded_actions := embedded_actions.get(old_folder.id):
                    embedded_actions_copies = folder_embedded_actions.copy()
                    embedded_actions_copies.parent_res_id = new_folder.id
                children_default = {"folder_id": new_folder.id}
                owner_id_in_default = (default or {}).get("owner_id") is not None
                if owner_id_in_default:
                    children_default.update(owner_id=default["owner_id"])

                if new_folder._is_descendant_of(old_folder):
                    _debug.logic("copy_refused", reason="into_own_descendant")
                    raise UserError(
                        _(
                            "You cannot copy a folder into itself or into one of its own descendants."
                        )
                    )
                old_folder.children_ids.with_context(
                    documents_copy_skip_rename=True
                ).copy(children_default)

                new_documents[documents_order[old_folder.id]] = new_folder
                if (
                    is_manager
                    and old_folder._is_company_root_folder()
                    and not owner_id_in_default
                ):
                    new_folder.owner_id = old_folder.owner_id

        if not skip_documents and (
            documents_sudo := (self - shortcuts - folders).sudo()
        ):
            _debug.pipeline("copy_binaries", documents=documents_sudo)
            new_binaries_sudo = documents_sudo._copy_with_access(default=default)
            for old_document_sudo, new_binary_sudo in zip(
                documents_sudo, new_binaries_sudo, strict=True
            ):
                new_documents[documents_order[old_document_sudo.id]] = (
                    new_binary_sudo.sudo(False)
                )
                if (
                    is_manager
                    and "owner_id" not in (default or {})
                    and (
                        not old_document_sudo.owner_id
                        and not old_document_sudo.folder_id
                    )
                ):
                    new_binary_sudo.owner_id = False
            self.browse(
                [
                    new_binary_sudo.id
                    for new_binary_sudo in new_binaries_sudo
                    if new_binary_sudo.sudo(self.env.su)._cannot_create_sibling()
                ]
            ).sudo().write({"folder_id": False})

            if to_copy_attachment_sudo := documents_sudo._copy_attachment_filter(
                default
            ):
                record_link = self._get_copy_record_link(default)
                new_attachments_iterator = iter(
                    to_copy_attachment_sudo.attachment_id.with_context(
                        no_document=True
                    ).copy()
                )
                with self.env.protecting(
                    self._get_fields_to_recompute(depends=["attachment_id"]),
                    new_binaries_sudo,
                ):
                    for old_document_sudo, new_binary_sudo in zip(
                        documents_sudo, new_binaries_sudo, strict=True
                    ):
                        if old_document_sudo in to_copy_attachment_sudo:
                            new_attachment = next(new_attachments_iterator)
                            new_binary_sudo.write(
                                {"attachment_id": new_attachment.id, **record_link}
                            )

        _debug.lifecycle("copy", source=self, slots=len(new_documents))
        return self.browse(
            [new_document.id for new_document in new_documents if new_document]
        )

    def _get_copy_record_link(self, default: dict | None) -> dict:
        default = default or {}
        res_model = default.get("res_model", self.env.context.get("default_res_model"))
        res_id = default.get("res_id", self.env.context.get("default_res_id"))
        if res_model and res_id:
            return {"res_model": res_model, "res_id": res_id}
        return {"res_model": False, "res_id": False}

    def copy_data(self, default: dict | None = None) -> list[dict]:
        default = dict(default or {})
        if "user_folder_id" in default:
            self._clean_vals_for_user_folder_id(default)
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for document, vals in zip(self, vals_list, strict=True):
                vals["name"] = (
                    document.name
                    if self.env.context.get("documents_copy_skip_rename")
                    else _("%s (copy)", document.name)
                )
        if "legal_number" in self._fields and "legal_number" not in default:
            for document, vals in zip(self, vals_list, strict=True):
                if document.legal_number:
                    vals["legal_number"] = _("%s (copy)", document.legal_number)
        for vals in vals_list:
            vals["access_ids"] = default.get("access_ids", False)
            if "owner_id" not in vals:
                vals["owner_id"] = self.env.user.id
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def unlink(self) -> bool:
        to_delete = self._with_descendants_sudo().sudo(False)
        removable_parent_folders = self._get_removable_parent_folders()
        removable_attachments = to_delete.attachment_id.filtered(
            lambda a: a.res_model != "document.document"
        )
        _debug.lifecycle(
            "unlink",
            documents=self,
            with_descendants=len(to_delete),
            attachments=len(removable_attachments),
            emptied_parents=len(removable_parent_folders),
        )

        with _debug.perf("unlink_super", cr=self.env.cr, documents=to_delete):
            res = super(DocumentsDocument, to_delete).unlink()

        if removable_attachments:
            removable_attachments.unlink()
        if removable_parent_folders:
            with contextlib.suppress(AccessError):
                removable_parent_folders.unlink()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unauthorized(self) -> None:
        try:
            self.check_access("unlink")
        except UserError as e:
            _debug.logic("unlink_refused", reason="no_unlink_access", documents=self)
            raise UserError(_("You are not allowed to delete all these items.")) from e
        self._raise_if_unauthorized_archive()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_company_folders(self) -> None:
        self._raise_if_used_folder()

    @api.depends("document_token")
    def _compute_access_token(self) -> None:
        for document in self:
            document.access_token = f"{document.document_token}o{document.id or 0:x}"

    @api.depends("access_token")
    def _compute_access_url(self) -> None:
        for document in self:
            document.access_url = f"{document.sudo().get_base_url()}/odoo/documents/{quote(document.access_token, safe='')}"

    @api.depends("create_activity_type_id", "create_activity_user_id")
    def _compute_create_activity_option(self) -> None:
        to_activate = self.filtered(
            lambda d: d.create_activity_type_id and d.create_activity_user_id
        )
        to_activate.create_activity_option = True
        (self - to_activate).create_activity_option = False

    @api.depends("folder_id", "company_id")
    @api.depends_context("uid", "allowed_company_ids", "documents_show_parent_name")
    def _compute_display_name(self) -> None:
        accessible_records = self._filtered_access("read")
        not_accessible_records = self - accessible_records
        if _debug.logic.enabled and not_accessible_records:
            _debug.logic("display_name_masked", documents=not_accessible_records)
        not_accessible_records.display_name = _("Restricted")
        folders = accessible_records.filtered(lambda d: d.type == "folder")
        for record in folders:
            if record.user_permission != "none":
                record.display_name = (
                    record.name
                    if not self.env.context.get("documents_show_parent_name")
                    or not record.folder_id
                    else _(
                        "%(record)s (in %(parent)s)",
                        record=record.name,
                        parent=record.folder_id.name,
                    )
                )
            else:
                record.display_name = _("Restricted Folder")

        for record in accessible_records - folders:
            record.display_name = record.name

    @api.depends("type")
    def _compute_is_folder(self):
        for document in self:
            document.is_folder = document.type == "folder"

    def _order_by_sql_is_folder(self, field, alias, direction, nulls, query):
        # the term agrees with the value: folders are True, so "is_folder desc"
        # lists them first, as the list view and the search model ask
        return self._order_value_to_sql(
            SQL("(%s = 'folder')", SQL.identifier(alias, "type")),
            direction,
            nulls,
            query,
        )

    @api.depends("name", "type", "shortcut_document_id.name")
    def _compute_file_extension(self) -> None:
        for record in self:
            if record.type != "binary":
                record.file_extension = False
            elif record.shortcut_document_id.name:
                file_extension = _normalize_file_extension(
                    get_extension(record.shortcut_document_id.name.strip())
                )
                record.file_extension = file_extension or False
            elif record.name:
                record.file_extension = (
                    _normalize_file_extension(get_extension(record.name.strip()))
                    or False
                )

    @api.depends(
        "attachment_id.file_size", "shortcut_document_id.attachment_id.file_size"
    )
    def _compute_file_size(self) -> None:
        shortcuts = self.filtered("shortcut_document_id")
        for document in self - shortcuts:
            document.file_size = document.attachment_id.file_size
        for document in shortcuts:
            document.file_size = document.shortcut_document_id.file_size

    @api.depends(
        "attachment_id",
        "url",
        "shortcut_document_id",
        "shortcut_document_id.name",
        "shortcut_document_id.url_preview_image",
    )
    def _compute_name_and_preview(self) -> None:
        shortcuts = self.filtered("shortcut_document_id")
        for record in self - shortcuts:
            if record.attachment_id:
                record.name = record.attachment_id.name
                record.url_preview_image = False
            elif record.url and not record.name:
                record.name = record.url

        for shortcut in shortcuts:
            shortcut.name = shortcut.name or shortcut.shortcut_document_id.name
            shortcut.url_preview_image = (
                shortcut.url_preview_image
                or shortcut.shortcut_document_id.url_preview_image
            )

    def _mark_url_preview_pending(self, documents: DocumentsDocument) -> None:
        to_fetch = documents.filtered(
            lambda d: d.type == "url" and d.url and not d.shortcut_document_id
        )
        if not to_fetch:
            return
        _debug.pipeline("url_preview_pending", documents=to_fetch)
        to_fetch.url_preview_pending = True
        self._trigger_url_preview_cron()

    @api.model
    def _cron_update_url_preview(self, limit: int = 200) -> None:
        # sudo for the same reason `_cron_refresh_expiration_state` needs it:
        # a system sweep must not be scoped to the cron user's readable set.
        documents = self.sudo().search(
            [("url_preview_pending", "=", True), ("type", "=", "url")], limit=limit
        )
        if not documents:
            return
        _debug.pipeline("url_preview_pass", documents=documents, limit=limit)
        session = link_preview.get_link_preview_session(self.env)
        for document in documents:
            vals = {"url_preview_pending": False}
            with _debug.perf("url_preview_fetch", document=document) as span:
                preview = (
                    link_preview.get_link_preview_from_url(document.url, session)
                    if document.url
                    else None
                )
                span.set(found=bool(preview))
            if preview:
                if preview.get("og_title") and document.name in (False, document.url):
                    vals["name"] = preview["og_title"]
                if preview.get("og_image"):
                    vals["url_preview_image"] = preview["og_image"]
            document.write(vals)
            if not modules.module.current_test:
                self.env.cr.commit()

        if len(documents) == limit:
            _debug.pipeline("url_preview_requeued", documents=len(documents))
            self._trigger_url_preview_cron()

    @api.depends("checksum", "mimetype")
    def _compute_is_multipage(self) -> None:
        for document in self:
            document.is_multipage = bool(document._get_is_multipage())

    @api.depends(
        "attachment_id",
        "attachment_id.res_model",
        "attachment_id.res_id",
        "shortcut_document_id.res_model",
        "shortcut_document_id.res_id",
    )
    def _compute_res_record(self) -> None:
        for record in self:
            attachment = record.attachment_id
            if attachment:
                record.res_model = (
                    attachment.res_model != "document.document" and attachment.res_model
                ) or False
                record.res_id = (
                    attachment.res_model != "document.document" and attachment.res_id
                ) or False
            if record.shortcut_document_id:
                record.res_model = record.shortcut_document_id.res_model
                record.res_id = record.shortcut_document_id.res_id

    @api.depends("res_model", "res_id")
    def _compute_res_name(self) -> None:
        linked = self.filtered(lambda d: d.res_id and d.res_model)
        for res_model, documents in linked.grouped("res_model").items():
            if res_model not in self.env:
                continue
            with contextlib.suppress(MissingError, AccessError):
                self.env[res_model].browse(documents.mapped("res_id")).exists().mapped(
                    "display_name"
                )

        (self - linked).res_name = False
        for record in linked:
            if record.res_model not in self.env:
                record.res_name = False
                continue
            try:
                record.res_name = (
                    self.env[record.res_model].browse(record.res_id).display_name
                )
            except MissingError:
                record.res_name = False
            except AccessError:
                _debug.logic(
                    "res_name_masked",
                    document=record,
                    res_model=record.res_model,
                )
                record.res_name = _("Restricted")

    @api.depends(
        "checksum",
        "mimetype",
        "attachment_id.type",
        "shortcut_document_id.thumbnail",
        "shortcut_document_id.thumbnail_status",
    )
    def _compute_thumbnail(self) -> None:
        for document in self:
            if document.shortcut_document_id:
                document.thumbnail = document.shortcut_document_id.thumbnail
                document.thumbnail_status = (
                    document.shortcut_document_id.thumbnail_status
                )
            elif document.mimetype and (
                document.mimetype.startswith("application/pdf")
                or document.mimetype.startswith("image/webp")
                or (
                    document.mimetype.startswith("image/")
                    and document.attachment_id.type == "cloud_storage"
                )
            ):
                document.thumbnail = False
                document.thumbnail_status = "client_generated"
            elif document.mimetype and document.mimetype.startswith("image/"):
                content = document.attachment_id.sudo()._get_content_prefix()
                # Any decoding failure is an ERROR THUMBNAIL, never an
                # exception. This compute is stored, so it runs inside the
                # `create`/`write` that carried the file: whatever escapes here
                # aborts that write and loses the upload. The two exceptions
                # named before were the two `odoo.tools.image` raises on its
                # own; Pillow raises its own types straight through, and
                # `DecompressionBombError` is the one that is reachable on
                # purpose -- a uniform 16000x16000 PNG is 250 KB on the wire and
                # 256 Mpx once decoded, so no upload size limit bounds it, and
                # `/documents/upload/<token>` accepts it from an unauthenticated
                # visitor holding an edit link.
                try:
                    thumbnail = (
                        image_process(
                            content,
                            size=(200, 140),
                            crop="center",
                            # Bound the DECODE, not just the download. Pillow
                            # only refuses above twice its own MAX_IMAGE_PIXELS;
                            # between one and two times it warns and decodes
                            # anyway, so a 410 KB, 12000x12000 RGB PNG arriving
                            # on the public upload route allocated ~550 MB and
                            # SUCCEEDED -- a better denial primitive than the
                            # one that raised, because it can be repeated and
                            # logs nothing. `verify_resolution` reads the header
                            # and refuses past `IMAGE_MAX_RESOLUTION` (50 Mpx)
                            # before any pixel is decoded, as `html_editor` and
                            # `web_unsplash` already do on their upload paths.
                            # Past it the file is still stored and served; only
                            # its preview is skipped.
                            verify_resolution=True,
                        )
                        if content
                        else None
                    )
                except Exception:
                    thumbnail = None
                    _logger.warning(
                        "Documents: could not build a thumbnail for %r (%s)",
                        document.name,
                        document.mimetype,
                        exc_info=True,
                    )
                document.thumbnail = base64.b64encode(thumbnail) if thumbnail else False
                document.thumbnail_status = "present" if thumbnail else "error"
                if _debug.logic.enabled and not thumbnail:
                    _debug.logic(
                        "thumbnail_failed",
                        document=document,
                        mimetype=document.mimetype,
                    )
            else:
                document.thumbnail = False
                document.thumbnail_status = False

    @api.depends("type")
    def _compute_deletion_delay(self) -> None:
        folders = self.filtered(lambda d: d.type == "folder")
        folders.deletion_delay = self.get_deletion_delay()
        (self - folders).deletion_delay = False

    @api.depends("res_model")
    def _compute_res_model_name(self) -> None:
        for record in self:
            if record.res_model:
                record.res_model_name = (
                    self.env["ir.model"]._get(record.res_model).display_name
                )
            else:
                record.res_model_name = False

    def _inverse_file_extension(self) -> None:
        for record in self:
            file_extension = (
                _normalize_file_extension(record.file_extension)
                if record.file_extension
                else False
            )
            (record | record.shortcut_ids).file_extension = file_extension

    def _owning_record_link(self) -> tuple:
        """Where this document's file belongs: the linked record, or itself.

        `res_model` can name a model the registry no longer has -- the module
        that owned it was uninstalled and the string stayed behind on the row.
        That is a dangling link, not an error, and `_compute_res_name` and
        `_inverse_res_record` already read it that way. Two write paths did not,
        and they are the ones that hurt: `_write_attach_empty_document` indexed
        `self.env[res_model]` unguarded and raised a bare `KeyError: '<model>'`
        -- reaching the client as a 500 when someone fulfilled an upload request
        against a record whose module had since been uninstalled -- and
        `_write_version_existing` stamped the dead name onto a freshly created
        attachment, which `ir.attachment` then refuses to read at all, because it
        denies access to anything it cannot access-check.

        The expression this replaces was written out at three call sites, one of
        them in the controller, which is why the guard was missing from two of
        them.
        """
        self.check_singleton()
        if self.res_model and self.res_model in self.env:
            return self.res_model, self.res_id
        return "document.document", self.id

    def _inverse_res_record(self) -> None:
        attachments_by_target = defaultdict(lambda: self.env["ir.attachment"])
        self_link_targets = set()
        for record in self:
            attachment = record.attachment_id

            res_model, res_id = record.res_model, record.res_id
            if not res_model:
                res_model = "document.document"
                res_id = record.id
                self_link_targets.add((res_model, res_id))

            if attachment and (attachment.res_model, attachment.res_id) != (
                res_model,
                res_id,
            ):
                attachments_by_target[(res_model, res_id)] |= attachment

        for (res_model, res_id), attachments in attachments_by_target.items():
            if (
                not self.env.su
                and (res_model, res_id) not in self_link_targets
                and res_model in self.env
            ):
                self.env[res_model].browse(res_id).check_access("write")
            attachments.sudo().with_context(no_document=True).write(
                {"res_model": res_model, "res_id": res_id}
            )

    def action_move_folder(
        self, target: str, before_folder_id: int | bool = False
    ) -> bool | None:
        self.check_singleton()
        if self.type != "folder" or not self.active:
            _debug.logic(
                "move_folder_noop",
                document=self,
                type=self.type,
                active=self.active,
            )
            return None

        values = {"user_folder_id": target}
        sibling_folders_domain = (
            Domain("type", "=", "folder")
            & Domain("id", "!=", self.id)
            & Domain("user_folder_id", "=", target)
        )

        if before_folder := self.browse(before_folder_id).exists():
            located_after_domain = Domain("sequence", ">", before_folder.sequence) | (
                Domain("sequence", "=", before_folder.sequence)
                & Domain("id", "<=", before_folder_id)
            )
            folders_to_resequence_domain = sibling_folders_domain & located_after_domain
            folders_to_resequence_sudo = self.sudo().search(
                folders_to_resequence_domain
            )
            if (
                folders_to_resequence_sudo
                and before_folder == folders_to_resequence_sudo[0]
            ):
                _debug.pipeline(
                    "folder_resequence",
                    folder=self,
                    before=before_folder,
                    siblings=len(folders_to_resequence_sudo),
                )
                values["sequence"] = before_folder.sequence
                new_sequence = before_folder.sequence + 1
                for folder_sudo in folders_to_resequence_sudo:
                    if folder_sudo.sequence >= new_sequence:
                        break
                    folder_sudo.sequence = new_sequence
                    new_sequence += 1
                return self.write(values)

        if (
            result := self.env["document.document"]
            .sudo()
            .search_read(
                sibling_folders_domain,
                fields=["sequence"],
                order="sequence DESC",
                limit=1,
            )
        ):
            values["sequence"] = result[0]["sequence"] + 1

        return self.write(values)

    def action_create_shortcut(
        self, location_user_folder_id: str | None = None
    ) -> DocumentsDocument:
        if not self.ids:
            return self.browse()

        if location_user_folder_id is None and len({d.folder_id.id for d in self}) > 1:
            _debug.logic("shortcut_refused", reason="ambiguous_destination")
            raise UserError(
                _("A destination is required when creating multiple shortcuts at once.")
            )
        if location_user_folder_id is False:
            _debug.logic("shortcut_refused", reason="ambiguous_location")
            raise UserError(_("Ambiguous shortcut target location."))
        if location_user_folder_id is not None:
            user_folder = self._parse_user_folder(location_user_folder_id)
            location_folder_id = (
                user_folder.folder_id
                if user_folder is not None and user_folder.is_folder
                else False
            )
        else:
            location_folder_id = None

        location = (
            self.browse(location_folder_id)
            if location_folder_id is not None
            else self.folder_id
        )
        if location_folder_id and location.shortcut_document_id:
            return self.action_create_shortcut(str(location.shortcut_document_id.id))

        if location:
            if location.user_permission != "edit":
                _debug.logic("shortcut_refused", reason="location_not_editable")
                raise AccessError(_("You are not allowed to write in this folder."))
        elif location_user_folder_id == UserFolder.COMPANY and not self.env.su:
            targets = self.shortcut_document_id | self.filtered(
                lambda d: not d.shortcut_document_id
            )
            if any(t.type == "folder" for t in targets) and not self.env.user.has_group(
                "document.group_documents_manager"
            ):
                self._raise_company_folder_manager_only()

        (
            self.shortcut_document_id
            | self.filtered(lambda d: not d.shortcut_document_id)
        ).check_access("read")

        return (
            self.sudo()
            .create(
                [
                    {
                        "user_folder_id": str(location.id)
                        if location
                        else location_user_folder_id,
                        "shortcut_document_id": (
                            target := document.shortcut_document_id or document
                        ).id,
                        **self._shortcut_access_defaults(target),
                        "access_ids": [
                            Command.create(
                                {
                                    "partner_id": access.partner_id.id,
                                    "role": access.role,
                                }
                            )
                            for access in target.access_ids
                            if access.role
                        ],
                        **{
                            field_name: (
                                value.id
                                if isinstance(
                                    (value := target[field_name]), models.Model
                                )
                                else value
                            )
                            for field_name in self._get_fields_shortcuts_copy()
                        },
                    }
                    for document in self
                ]
            )
            .sudo(False)
        )

    def action_view_access_log(self) -> dict:
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "document.documents_access_log_action"
        )
        return action | {
            "display_name": _("Access Log: %s", self.name),
            "domain": [("document_id", "=", self.id)],
            "context": {"search_default_group_partner": 1},
        }

    def toggle_lock(self) -> None:
        self.check_singleton()
        _debug.lifecycle("toggle_lock", document=self, locked_by=self.lock_uid)
        if self.lock_uid:
            self.lock_uid = False
        else:
            self.lock_uid = self.env.uid

    def _check_user_favorite_access(self) -> None:
        self._check_access_or_raise(
            "read", _("You are not allowed to access these documents.")
        )

    # compute_sudo=False, unlike the mixin's default: the compute below masks
    # the value for documents this user may not access, and _filtered_access
    # answers "yes" to everything when it runs sudo.
    is_user_favorite = fields.Boolean(compute_sudo=False)

    @api.depends("favorite_user_ids")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_is_user_favorite(self) -> None:
        # A document you may no longer access reads as not-favorited, rather
        # than as whatever the relation still says. Field reads on this model
        # are not gated by user_permission, so the mixin's plain membership
        # test would answer for records the rest of the UI hides.
        favorited = self._filtered_access("read").filtered(
            lambda document: self.env.user in document.favorite_user_ids
        )
        favorited.is_user_favorite = True
        (self - favorited).is_user_favorite = False

    def action_archive(self) -> bool | None:
        if not self:
            return None

        if locked_by_other := self._locked_by_other():
            _debug.logic(
                "archive_refused", reason="locked_by_other", documents=locked_by_other
            )
            raise UserError(
                _(
                    "“%(name)s” is locked by %(user)s and cannot be sent to "
                    "the trash by another user.",
                    name=locked_by_other[0].name,
                    user=locked_by_other[0].lock_uid.name,
                )
            )

        to_archive_sudo = self._with_descendants_sudo()
        active_documents = to_archive_sudo.filtered(self._active_name).sudo(False)
        if not active_documents:
            _debug.logic("archive_noop", reason="nothing_active", documents=self)
            return None

        active_documents._check_access_or_raise(
            "unlink", self._archive_denied_message()
        )

        active_documents._raise_if_unauthorized_archive()
        active_documents._raise_if_used_folder()
        deletion_date = self._next_deletion_date()
        log_message = _(
            "This file has been sent to the trash and will be deleted forever on the %s",
            fields.Date.to_string(deletion_date),
        )
        active_documents._message_log_batch(
            bodies={doc.id: log_message for doc in active_documents}
        )
        _debug.lifecycle(
            "archive",
            documents=active_documents,
            requested=len(self),
            deletion_date=deletion_date,
        )
        # The stamp itself happens in `_write_check_active_after`, on the
        # active transition the `super()` call below performs, so that a path
        # which never comes through here is covered too. Both read
        # `_next_deletion_date`, so the promise above and the date the purge
        # reads cannot drift.
        return super(
            DocumentsDocument,
            active_documents.with_context(documents_archiving=True),
        ).action_archive()

    def action_unarchive(self) -> bool | None:
        self_archived = self.filtered(lambda d: not d.active)
        if not self_archived:
            return None
        archived_top_parent_documents = (
            self.env["document.document"]
            .sudo()
            .search(
                Domain.AND(
                    (
                        Domain("id", "parent_of", self_archived.ids),
                        Domain("id", "not in", self_archived.ids),
                        Domain("active", "=", False),
                        Domain("folder_id", "=", False)
                        | Domain("folder_id.active", "=", True),
                    )
                )
            )
            .sudo(False)
        )
        if archived_top_parent_documents:
            _debug.logic(
                "unarchive_refused",
                reason="archived_parent_folders",
                folders=archived_top_parent_documents,
            )
            raise UserError(
                _(
                    "Item(s) you wish to restore are included in archived folders. "
                    "To restore these items, you must restore the following including folders instead:\n"
                    "- %(folders_list)s",
                    folders_list="\n-".join(
                        archived_top_parent_documents.mapped("name")
                    ),
                )
            )

        to_unarchive_candidate_documents = (
            self.env["document.document"]
            .with_context(active_test=False)
            .search([("id", "child_of", self_archived.ids)])
        )

        seen_documents, to_unarchive_ids = set(), set()

        def add_if_can_be_restored(doc: DocumentsDocument) -> bool:
            if doc in seen_documents or seen_documents.add(doc):
                return doc.id in to_unarchive_ids
            if (
                not doc.folder_id
                or doc.folder_id.sudo().active
                or add_if_can_be_restored(doc.folder_id)
            ):
                to_unarchive_ids.add(doc.id)
                return True
            return False

        for document in to_unarchive_candidate_documents:
            add_if_can_be_restored(document)
        to_unarchive_documents = to_unarchive_candidate_documents.filtered(
            lambda d: d.id in to_unarchive_ids
        )
        log_message = _("This document has been restored.")
        to_unarchive_documents._message_log_batch(
            bodies={doc.id: log_message for doc in to_unarchive_documents}
        )
        _debug.lifecycle(
            "unarchive",
            documents=to_unarchive_documents,
            candidates=len(to_unarchive_candidate_documents),
        )
        return super(DocumentsDocument, to_unarchive_documents).action_unarchive()

    def add_documents_attachment(
        self, res_model: str, res_id: int, is_public: bool = False
    ) -> list[dict]:
        origins = self.attachment_id
        new_attachments = origins.copy(
            {"res_model": res_model, "res_id": res_id, "public": is_public}
        )
        for origin, copied in zip(origins, new_attachments, strict=True):
            copied.original_id = origin.id

        if is_public:
            new_attachments.generate_access_token()

        return [attachment._get_media_info() for attachment in new_attachments]

    def _copy_attachment_filter(self, default: dict | None) -> DocumentsDocument:
        if default and "attachment_id" in default:
            return self.env["document.document"]
        return self.filtered("attachment_id")

    def _copy_with_access(self, default: dict | None) -> DocumentsDocument:
        if not self:
            return self
        res = super().copy(default=default)
        if default and "access_ids" in default:
            return res
        access_vals_list = []
        for doc, doc_copied in zip(self, res, strict=True):
            owner_partner = doc_copied.owner_id.partner_id
            doc_access_to_have = doc.access_ids.filtered("role")
            doc_access_to_create = doc_access_to_have.filtered(
                lambda a, doc_copied=doc_copied, owner_partner=owner_partner: (
                    a.partner_id not in doc_copied.access_ids.partner_id | owner_partner
                )
            )
            access_vals_list += doc_access_to_create.copy_data(
                default={"document_id": doc_copied.id}
            )
        self.env["document.access"].sudo().create(access_vals_list)
        return res

    def get_deletion_delay(self) -> int:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("document.deletion_delay", 30)
        )

    def is_folder_containing_document(self) -> bool:
        self.check_singleton()
        return bool(
            self.env["document.document"]
            .sudo()
            .search_count(
                [("id", "child_of", self.id), ("type", "!=", "folder")],
                limit=1,
            )
        )

    def _get_is_multipage(self) -> bool | None:
        decoded = self.attachment_id._get_pdf_raw() if self.attachment_id else None
        if decoded is None:
            return None
        if modules.module.current_test and not decoded.lstrip().startswith(b"%PDF"):
            # Without wkhtmltopdf a test run renders reports as HTML; a
            # document with no PDF header cannot have pages to count.
            _logger.info(
                "Skip _get_is_multipage of %r: html content detected in pdf document while in testing mode",
                self.name,
            )
            return False
        try:
            return len(PdfReader(io.BytesIO(decoded), strict=False).pages) > 1
        except Exception:
            _logger.warning(
                "Impossible to count pages in %r: malformed PDF",
                self.name,
                exc_info=True,
            )
            return False

    @api.model
    def _get_fields_shortcuts_copy(self) -> set:
        return {
            "company_id",
            "is_access_via_link_hidden",
            "is_multipage",
            "partner_id",
            "type",
            "url",
        }

    @api.readonly
    @api.model
    def get_document_max_upload_limit(self) -> int | None:
        ICP = self.env["ir.config_parameter"].sudo()
        for key in ("document.max_fileupload_size", "web.max_file_upload_size"):
            value = ICP.get_param(key, default=None)
            if value is None:
                continue
            try:
                return int(value) or None
            except ValueError:
                _logger.error("invalid %s: %r", key, value)
        return odoo.http.DEFAULT_MAX_CONTENT_LENGTH

    @api.model
    def _get_details_panel_res_models(self) -> list[str]:
        # Each document_* bridge adds the model it links documents to; these
        # two have no bridge module to declare them from.
        return ["purchase.order", "sale.order"]

    @api.readonly
    @api.model
    def get_details_panel_res_models(self) -> list:
        return [
            model
            for model in self._get_details_panel_res_models()
            if (res_model := self.env.get(model)) is not None
            and res_model.has_access("read")
        ]

    @api.model
    def _get_traceback_folder_sudo(self) -> DocumentsDocument:
        folder_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("document.support_folder", 0)
        )
        folder_sudo = self.env["document.document"].sudo().browse(folder_id)
        if not folder_sudo or not folder_sudo.exists():
            _debug.lifecycle("support_folder_created", previous=folder_id)
            folder_sudo = (
                self.env["document.document"]
                .sudo()
                .create(
                    {
                        "name": self.env._("Support"),
                        "type": "folder",
                        "access_internal": "none",
                        "access_via_link": "none",
                    }
                )
            )
            self.env["ir.config_parameter"].sudo().set_param(
                "document.support_folder", folder_sudo.id
            )
        return folder_sudo

    def _with_descendants_sudo(self) -> DocumentsDocument:
        return (
            self.sudo()
            .with_context(active_test=False)
            .search([("id", "child_of", self.ids)])
        )

    def _get_removable_parent_folders(self) -> DocumentsDocument:
        folders_sudo = self.sudo().with_context(active_test=False).folder_id
        removable_sudo = folders_sudo.filtered(
            lambda folder: (
                not (folder.children_ids - self.sudo())
                and not folder.active
                and folder.id not in self.ids
            )
        )
        return removable_sudo.with_env(self.env)

    @api.model
    def _get_domain_gc_clear_bin(self) -> list:
        """Purge what the trash SAID it would purge, on the day it said.

        This used to re-derive the date as `write_date <= now - delay`, which
        is a different quantity from the one `action_archive` writes into the
        chatter ("will be deleted forever on ..."):

        - any later write to a trashed document -- a rename, a stored
          recompute, a bridge detaching `res_model` -- restarted the countdown
          silently, with no new message and nothing in the UI saying so;
        - changing `document.deletion_delay` retroactively moved the date of
          every document already in the trash, in both directions; lowering it
          could purge, on the next cron run, documents whose own message
          promised them weeks more.

        `deletion_date` is stamped once, when the document is archived, so the
        promise and the mechanism are the same value. `_gc_clear_bin` still
        skips rows with no date -- a document archived by a bare
        `write({"active": False})` under `documents_archiving`, or by an older
        version before the migration -- rather than inventing one for them.
        """
        return [
            ("active", "=", False),
            ("deletion_date", "!=", False),
            ("deletion_date", "<=", fields.Date.today()),
        ]

    def _get_access_action(
        self, access_uid: int | None = None, force_website: bool = False
    ) -> dict:
        self.check_singleton()
        if (
            access_uid
            and not force_website
            and self.active
            and self.env.user.has_group("document.group_documents_user")
        ):
            url_params = url_encode(
                {
                    "documents_init_document_id": self.id,
                    "view_id": self.env.ref("document.document_view_kanban").id,
                    "menu_id": self.env.ref("document.menu_root").id,
                    "folder_id": self.folder_id.id,
                }
            )

            return {
                "type": "ir.actions.act_url",
                "url": f"/odoo/action-document.document_action?{url_params}",
            }
        return super()._get_access_action(
            access_uid=access_uid, force_website=force_website
        )

    def _get_copy_shortcuts_destinations(
        self, shortcuts: DocumentsDocument, default: dict | None
    ) -> Any:
        default = default or {}
        folder_id = default.get("folder_id")
        user_folder_id = default.get("user_folder_id")
        prefetch_ids = None
        candidates = {}

        if user_folder := self._parse_user_folder(user_folder_id):
            if user_folder.is_folder:
                candidates[self.browse(user_folder.folder_id)] = shortcuts
            else:
                return ((str(user_folder), shortcuts),)
        elif folder_id is not None:
            candidates[self.browse(folder_id)] = shortcuts
        else:
            candidates = shortcuts.grouped("folder_id")
            prefetch_ids = shortcuts.folder_id.ids

        targets_per_destination = defaultdict(self.browse)
        for destination, destination_shortcuts in candidates.items():
            if isinstance(destination, str):
                pass
            elif (
                not self.env.su
                and destination
                and destination.with_prefetch(prefetch_ids).user_permission != "edit"
            ):
                destination = UserFolder.MY
            else:
                destination = str(destination.id)
            targets_per_destination[destination] |= destination_shortcuts
        return targets_per_destination.items()

    @api.model
    def _get_fields_to_recompute(self, depends: list) -> set | list:
        if not depends:
            return []

        fields_to_recompute = set()
        fields_compute_stored = {
            field
            for field in self._fields.values()
            if field.copy and field.store and field.compute
        }
        for field_dependence in (self._fields[depend] for depend in depends):
            fields_dependent = set(self.pool.get_dependent_fields(field_dependence))
            fields_to_recompute |= fields_compute_stored & fields_dependent

        return fields_to_recompute

    def _prepare_create_values(self, vals_list: list[dict]) -> list[dict]:
        old_vals_list = [vals.copy() for vals in vals_list]
        vals_list = super()._prepare_create_values(vals_list)
        _debug.pipeline("prepare_create_values", count=len(vals_list))
        folders = self.env["document.document"].browse(
            v["folder_id"] for v in vals_list if v.get("folder_id")
        )
        users = self.env["res.users"].browse(
            v["owner_id"] for v in vals_list if v.get("owner_id")
        )
        folders.fetch(
            (
                "access_internal",
                "access_via_link",
                "access_ids",
                "active",
                "company_id",
                "owner_id",
            )
        )
        (users | folders.owner_id).fetch(["partner_id"])
        self.browse(
            v["shortcut_document_id"]
            for v in vals_list
            if v.get("shortcut_document_id")
        ).check_access("read")
        vals_list_to_update_linked_record = []
        for vals, old_vals in zip(vals_list, old_vals_list, strict=True):
            owner = self.env["res.users"].browse(
                vals.get("owner_id", self.env.user.active and self.env.user.id)
            )
            if owner and not owner.active:
                _logger.warning(
                    "Documents: Creating document(s) as %s",
                    "superuser"
                    if owner.id == SUPERUSER_ID
                    else f"archived user (id={owner.id})",
                )
                owner = self.env["res.users"]
                vals["owner_id"] = False
                _debug.logic("owner_dropped", reason="inactive_user")

            vals_values = {"owner_id": owner.id}
            shortcut_target = self.browse()
            if vals.get("shortcut_document_id"):
                shortcut_target = self.browse(vals["shortcut_document_id"])

            folder = self.env["document.document"].browse(vals.get("folder_id", False))
            if folder:
                if not folder.active:
                    _debug.logic("create_refused", reason="archived_folder")
                    raise UserError(
                        self.env._(
                            "It is not possible to create documents in an archived folder."
                        )
                    )

                if not shortcut_target:
                    _debug.logic("access_defaults", by="folder", folder=folder)
                    vals_values.update(
                        {
                            "access_via_link": folder.access_via_link,
                            "access_internal": folder.access_internal,
                        }
                    )
                if folder.company_id:
                    vals_values["company_id"] = folder.company_id.id

            if shortcut_target:
                _debug.logic("access_defaults", by="shortcut_target")
                vals_values.update(
                    self._shortcut_access_defaults(shortcut_target)
                    | {
                        "is_access_via_link_hidden": shortcut_target.is_access_via_link_hidden,
                    }
                )

            vals.update((k, v) for k, v in vals_values.items() if k not in old_vals)
            provided_access_ids = self._validated_create_access_commands(
                old_vals.get("access_ids")
            )
            opted_out_of_inheritance = "access_ids" in old_vals and not any(
                command[0] == Command.CREATE for command in provided_access_ids
            )
            if (
                "shortcut_document_id" not in old_vals
                and not opted_out_of_inheritance
                and folder
                and (inherited_access_ids := folder._prepare_inherited_access_vals())
            ):
                partner_ids = [
                    command[2]["partner_id"]
                    for command in vals["access_ids"] or []
                    if command[0] == Command.CREATE and command[2]
                ]
                access_vals_to_add = [
                    v
                    for v in inherited_access_ids
                    if v["partner_id"] not in partner_ids
                ]
                _debug.pipeline(
                    "access_inherited", folder=folder, added=len(access_vals_to_add)
                )
                vals["access_ids"] = list(vals["access_ids"] or []) + [
                    Command.create(access_vals) for access_vals in access_vals_to_add
                ]

            if owner:
                vals["access_ids"] = list(vals["access_ids"] or [])
                for values in vals["access_ids"]:
                    if (
                        values[0] == Command.CREATE
                        and values[2]
                        and values[2]["partner_id"] == owner.partner_id.id
                    ):
                        values[2]["last_access_date"] = fields.Datetime.now()
                        break
                else:
                    vals["access_ids"] += [
                        Command.create(
                            {
                                "partner_id": owner.partner_id.id,
                                "last_access_date": fields.Datetime.now(),
                            }
                        )
                    ]

            if (
                "res_model" not in vals
                and "res_id" not in vals
                and isinstance(vals.get("attachment_id"), int)
            ):
                vals_list_to_update_linked_record.append(vals)

        if vals_list_to_update_linked_record:
            _debug.pipeline(
                "res_record_from_attachment",
                n=len(vals_list_to_update_linked_record),
            )
            attachment_by_id = (
                self.env["ir.attachment"]
                .browse(
                    [
                        vals["attachment_id"]
                        for vals in vals_list_to_update_linked_record
                    ]
                )
                .grouped("id")
            )
            for vals in vals_list_to_update_linked_record:
                attachment = attachment_by_id[vals["attachment_id"]]
                vals["res_model"] = (
                    False
                    if attachment.res_model == "document.document"
                    else attachment.res_model
                )
                vals["res_id"] = (
                    False
                    if attachment.res_model == "document.document"
                    else attachment.res_id
                )

        indexed = list(enumerate(zip(vals_list, old_vals_list, strict=True)))
        prepared_by_position = {}
        for res_model, group in groupby(
            indexed, lambda item: item[1][0].get("res_model")
        ):
            positions = [position for position, __ in group]
            prepared_by_position.update(
                zip(
                    positions,
                    self._prepare_create_values_for_model(
                        res_model,
                        [vals_list[position] for position in positions],
                        [old_vals_list[position] for position in positions],
                    ),
                    strict=True,
                )
            )
        return [prepared_by_position[position] for position in range(len(vals_list))]

    def _prepare_create_values_for_model(
        self, res_model: str | bool, vals_list: list[dict], pre_vals_list: list[dict]
    ) -> list[dict]:
        if (
            res_model
            and issubclass(self.pool[res_model], self.pool["mixin.documents"])
            and not self.env.context.get("no_document")
        ):
            return self.env[
                res_model
            ]._prepare_document_create_values_for_linked_records(
                res_model, vals_list, pre_vals_list
            )
        return vals_list

    @api.model
    def _pdf_split(
        self,
        new_files: list | None = None,
        open_files: list | None = None,
        vals: dict | None = None,
    ) -> DocumentsDocument:
        vals = vals or {}
        with _debug.perf("pdf_split", cr=self.env.cr) as span:
            new_attachments = self.env["ir.attachment"]._pdf_split(
                new_files=new_files, open_files=open_files
            )
            span.set(attachments=len(new_attachments))
        new_documents = self.create(
            [dict(vals, attachment_id=attachment.id) for attachment in new_attachments]
        )
        env_partner = self.env.user.partner_id
        documents_not_member = new_documents.filtered(
            lambda d: env_partner not in d.access_ids.partner_id
        )
        self.env["document.access"].sudo().create(
            [
                {
                    "document_id": doc.id,
                    "partner_id": env_partner.id,
                    "last_access_date": fields.Datetime.now(),
                }
                for doc in documents_not_member
            ]
        )
        return new_documents

    @api.autovacuum
    def _gc_clear_bin(self) -> tuple:
        limit = 1000
        with _debug.perf("gc_clear_bin", cr=self.env.cr) as span:
            expired = self.search(self._get_domain_gc_clear_bin(), limit=limit)
            removed = len(expired)
            expired.unlink()
            span.set(removed=removed, more=removed == limit)
        return removed, removed == limit

    def _raise_if_used_folder(self) -> None:
        if folder_ids := self.filtered(lambda d: d.type == "folder").ids:
            company_used_folders_domain = self.env[
                "res.company"
            ]._get_domain_used_folder_ids(folder_ids)
            if (
                self.env["res.company"]
                .sudo()
                .search_count(company_used_folders_domain, limit=1)
            ):
                _debug.logic(
                    "unlink_refused",
                    reason="folder_used_by_company",
                    folders=folder_ids,
                )
                raise ValidationError(
                    _("Impossible to delete folders used by other applications.")
                )
