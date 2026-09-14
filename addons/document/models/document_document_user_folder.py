from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.document.tools import UserFolder

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    @api.depends_context("uid", "allowed_company_ids")
    @api.depends(
        "folder_id",
        "folder_id.user_permission",
        "owner_id",
        "active",
        "user_permission",
    )
    def _compute_user_folder_id(self) -> None:
        SHARED = UserFolder.SHARED if not self.env.user.share else False
        self.user_folder_id = False
        active_documents = self.filtered("active")
        (self - active_documents).user_folder_id = UserFolder.TRASH
        for document in active_documents.filtered(
            lambda d: d.user_permission != "none"
        ):
            if document.folder_id:
                if document.folder_id.user_permission != "none":
                    document.user_folder_id = str(document.folder_id.id)
                else:
                    document.user_folder_id = SHARED
            elif self.env.user.share:
                document.user_folder_id = False
            elif not document.owner_id:
                document.user_folder_id = UserFolder.COMPANY
            elif document.owner_id == self.env.user:
                document.user_folder_id = UserFolder.MY
            else:
                document.user_folder_id = SHARED

    @api.model
    def _search_folder_id(self, operator: str, operand: int | list) -> list:
        if operator != "child_of":
            return Domain(Domain("folder_id", operator, operand), internal=True)
        values = {operand} if isinstance(operand, int) else set(operand)
        if len(values) > 1:
            _debug.logic("folder_search_refused", reason="many_child_of")
            raise UserError(
                _("Only one value can be searched for child of `folder_id`.")
            )
        value = values.pop()
        return self._get_domain_child_of_documents(
            Domain("folder_id", "=", value) | Domain("id", "=", value), value
        )

    def _search_user_folder_id(self, operator: str, operand: str | int | list) -> list:
        if operator not in ("in", "child_of"):
            return NotImplemented
        values = {operand} if isinstance(operand, str) else set(operand)
        if UserFolder.TRASH in values:
            _debug.logic("user_folder_search_refused", reason="trash")
            raise UserError(_("Searching on TRASH is not supported."))
        domain_parts = []
        folder_ids = []
        for value in values:
            user_folder = self._parse_user_folder(value)
            if user_folder is None and self.env.user.share:
                domain_parts.append(
                    Domain("folder_id", "=", False) | Domain("folder_id", "not any", [])
                )
            elif user_folder is None:
                domain_parts.append(Domain.FALSE)
            elif user_folder.kind == UserFolder.COMPANY:
                domain_parts.append(
                    Domain("folder_id", "=", False) & Domain("owner_id", "=", False)
                )
            elif user_folder.kind == UserFolder.MY:
                domain_parts.append(
                    Domain("folder_id", "=", False)
                    & Domain("owner_id", "=", self.env.user.id)
                )
            elif user_folder.kind == UserFolder.RECENT:
                domain_parts.append(
                    Domain(
                        "access_ids",
                        "any",
                        Domain("partner_id", "=", self.env.user.partner_id.id)
                        & Domain("last_access_date", "!=", False),
                    )
                )
            elif user_folder.kind == UserFolder.SHARED:
                domain_parts.append(
                    Domain("folder_id", "!=", False)
                    & Domain("folder_id", "not any", [])
                    | Domain("folder_id", "=", False)
                    & Domain("owner_id", "not in", [self.env.user.id, False])
                )
            elif user_folder.is_folder:
                folder_ids.append(user_folder.folder_id)
            else:
                _debug.logic(
                    "user_folder_search_refused",
                    reason="unsupported_kind",
                    kind=user_folder.kind,
                )
                raise UserError(_("Searching on %s is not supported.", user_folder))

        if folder_ids:
            domain_parts.append(
                Domain("folder_id", "in", folder_ids) & Domain("folder_id", "any", [])
            )

        domain = Domain.OR(domain_parts)

        _debug.logic(
            "user_folder_search",
            operator=operator,
            parts=len(domain_parts),
            folders=len(folder_ids),
        )

        if operator == "child_of":
            if len(values) > 1:
                _debug.logic("user_folder_search_refused", reason="many_child_of")
                raise UserError(
                    _("Only one value can be searched for children of `user_folder_id`")
                )
            return self._get_domain_child_of_documents(domain, values.pop())
        return domain

    @api.model
    def _parse_user_folder(self, value) -> UserFolder | None:
        try:
            return UserFolder.parse(value)
        except ValueError as error:
            _debug.logic("user_folder_parse_refused", value=value)
            raise UserError(_("Unexpected user_folder_id value %s", value)) from error

    @api.model
    def _clean_vals_for_user_folder_id(
        self, vals: dict, is_create: bool = False
    ) -> None:
        user_folder = self._parse_user_folder(vals.get("user_folder_id"))
        if user_folder is None:
            if (
                self.env.context.get("default_user_folder_id")
                and "folder_id" not in vals
                and "owner_id" not in vals
                and "default_folder_id" not in self.env.context
                and "default_owner_id" not in self.env.context
            ):
                user_folder = self._parse_user_folder(
                    self.env.context["default_user_folder_id"]
                )
            if user_folder is None:
                return
        vals["user_folder_id"] = str(user_folder)

        if user_folder.kind == UserFolder.COMPANY:
            new_vals = {"owner_id": False, "folder_id": False}
            if is_create and "access_internal" not in vals:
                new_vals["access_internal"] = "view"
        elif user_folder.kind == UserFolder.MY:
            if not self.env.user.active:
                _debug.logic("user_folder_refused", reason="inactive_user", kind="MY")
                raise UserError(_("Inactive user cannot create/move in 'My Drive'."))
            new_vals = {"owner_id": self.env.user.id, "folder_id": False}
        elif user_folder.kind == UserFolder.RECENT:
            _debug.logic("user_folder_refused", reason="virtual", kind="RECENT")
            raise UserError(_("Documents cannot be created or moved in 'Recent'."))
        elif user_folder.kind == UserFolder.SHARED:
            _debug.logic("user_folder_refused", reason="virtual", kind="SHARED")
            raise UserError(
                _("Documents cannot be created or moved in 'Shared With Me'.")
            )
        elif user_folder.kind == UserFolder.TRASH:
            _debug.logic("user_folder_refused", reason="virtual", kind="TRASH")
            raise UserError(_("Documents cannot be created or moved in the trash."))
        else:
            new_vals = {"folder_id": user_folder.folder_id}

        message = _("Conflicting values passed with user_folder_id.")
        if (folder_id := vals.get("folder_id")) and folder_id != new_vals["folder_id"]:
            _debug.logic(
                "user_folder_conflict", field="folder_id", kind=user_folder.kind
            )
            raise UserError(message)
        if (
            (owner_id := vals.get("owner_id"))
            and "owner_id" in new_vals
            and owner_id != new_vals["owner_id"]
        ):
            _debug.logic(
                "user_folder_conflict", field="owner_id", kind=user_folder.kind
            )
            raise UserError(message)
        _debug.logic(
            "user_folder_resolved", kind=user_folder.kind, sets=sorted(new_vals)
        )
        vals.update(new_vals)

    @api.model
    def _get_domain_child_of_documents(
        self, roots_domain: Domain, value: str | int
    ) -> Domain:
        if not isinstance(value, str | int):
            raise UserError(
                _(
                    "Only one string or number value can be searched for documents `child_of`."
                )
            )
        if value == UserFolder.SHARED:
            shared_roots = self.with_context(active_test=False).search_fetch(
                roots_domain, ["id"]
            )
            _debug.perf.count("child_of_shared_roots", roots=len(shared_roots))
            return Domain("id", "child_of", shared_roots.ids)
        candidates, top_level_folders = (
            query.select(
                *(
                    self._field_to_sql(query.table, fname, query)
                    for fname in ("id", "folder_id")
                )
            )
            for query in (
                self.with_context(active_test=False)._search([("type", "=", "folder")]),
                self.with_context(active_test=False)._search(
                    roots_domain & Domain("type", "=", "folder")
                ),
            )
        )
        children = SQL(
            """
        WITH RECURSIVE
            candidates as (%(candidates)s),
            top_level as (%(top_level_folders)s),
            children AS (
                SELECT id
                  FROM top_level
                 UNION ALL
                SELECT c.id
                  FROM candidates c
                  JOIN children f
                    ON c.folder_id = f.id
            )
        SELECT id FROM children
        """,
            candidates=candidates,
            top_level_folders=top_level_folders,
        )
        return roots_domain | Domain("folder_id", "any", children)
