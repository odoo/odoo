from collections import defaultdict
from typing import Any

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.document.tools import UserFolder, is_mimetype_inline_rendered

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    def _is_documents_manager(self) -> bool:
        return self.env.is_admin() or self.env.user.has_group(
            "document.group_documents_manager"
        )

    @api.model
    def _raise_company_folder_manager_only(self) -> None:
        raise AccessError(_("Only Documents Managers can create in company folder."))

    def _check_access_or_raise(self, operation: str, message: str) -> None:
        try:
            self.check_access(operation)
        except UserError as error:
            raise AccessError(message) from error

    @api.depends_context("uid", "allowed_company_ids")
    @api.depends(
        "access_ids",
        "access_internal",
        "access_via_link",
        "owner_id",
        "is_access_via_link_hidden",
        "company_id",
        "folder_id.access_ids",
        "folder_id.access_internal",
        "folder_id.access_via_link",
        "folder_id.owner_id",
        "folder_id.company_id",
        "shortcut_document_id",
        "shortcut_document_owner_id",
        "access_ids.role",
        "access_ids.expiration_date",
    )
    def _compute_user_permission(self) -> None:
        self.user_permission = "none"

        saved = self.filtered(lambda document: isinstance(document.id, int))
        for document in self - saved:
            document.user_permission = (
                document._origin.user_permission if document._origin else "edit"
            )
        if not saved:
            return

        self.flush_model(self._user_permission_domain_fields())
        self.env["document.access"].flush_model(
            ["document_id", "partner_id", "role", "expiration_date"]
        )

        documents_sudo = (
            self.env["document.document"].sudo().with_context(active_test=False)
        )
        in_scope = Domain("id", "in", saved.ids)
        company_domains = self._permission_company_domains()
        reachable = documents_sudo._search(
            in_scope
            & self._search_user_permission(
                "in", ["view", "edit"], company_domains=company_domains
            )
        )
        editable = documents_sudo._search(
            in_scope
            & self._search_user_permission(
                "in", ["edit"], company_domains=company_domains
            )
        )
        self.env.cr.execute(
            SQL(
                """SELECT reachable.id, reachable.id IN (%(editable)s)
                     FROM (%(reachable)s) AS reachable""",
                editable=editable.select(),
                reachable=reachable.select(),
            )
        )
        levels = {
            document_id: "edit" if is_editable else "view"
            for document_id, is_editable in self.env.cr.fetchall()
        }
        _debug.perf.count(
            "user_permission_computed", documents=saved, resolved=len(levels)
        )
        for document in saved:
            document.user_permission = levels.get(document.id, "none")

    @api.depends(
        "active",
        "user_permission",
        "folder_id.user_permission",
        "owner_id",
        "user_folder_id",
    )
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_user_can_move(self) -> None:
        active_documents = self.filtered("active")
        (self - active_documents).user_can_move = False
        if self.env.is_admin() or self.env.user.has_group(
            "document.group_documents_system"
        ):
            _debug.logic("user_can_move", by="system_group", documents=self)
            active_documents.user_can_move = True
            return
        owned_documents = active_documents.filtered(
            lambda doc: doc.owner_id == self.env.user
        )
        owned_documents.user_can_move = True
        if unowned_documents := active_documents - owned_documents:
            is_manager = self.env.user.has_group("document.group_documents_manager")
            for document in unowned_documents:
                document.user_can_move = (
                    document.user_permission == "edit"
                    and (
                        not document.folder_id
                        or document.folder_id.user_permission == "edit"
                    )
                    and (is_manager or document.user_folder_id != UserFolder.COMPANY)
                )

    def _search_user_permission(
        self,
        operator: str,
        value: list | str,
        exclude_ownership: bool = False,
        *,
        company_domains: dict | None = None,
        ignore_link: bool = False,
    ) -> Domain:
        if self.env.user._is_public():
            return Domain.FALSE
        searched_roles = {"view", "edit", "none"}
        if operator == "in":
            searched_roles.intersection_update(value)
        elif operator == "not in":
            searched_roles.difference_update(value)
        else:
            return NotImplemented

        searched_roles.discard("none")
        if not searched_roles:
            return Domain.FALSE
        searched_roles = list(searched_roles)

        if self.env.user.has_group("document.group_documents_system"):
            if searched_roles == ["view"]:
                return Domain.FALSE
            return Domain.OR(
                [
                    Domain("company_id", "in", self.env.companies.ids),
                    Domain("company_id", "not in", self.env.user.company_ids.ids),
                    Domain("company_id.active", "=", False),
                ]
            )

        company_domains = company_domains or self._permission_company_domains()
        any_except_disabled_and_archived_company = company_domains[
            "any_except_disabled_and_archived"
        ]
        direct_domain = self._direct_user_permission_domain(
            searched_roles,
            exclude_ownership=exclude_ownership,
            company_domains=company_domains,
            ignore_link=ignore_link,
        )
        if exclude_ownership:
            return direct_domain

        link_via_parent_domain = (
            Domain.FALSE
            if ignore_link
            else Domain.AND(
                [
                    any_except_disabled_and_archived_company,
                    [("access_via_link", "in", searched_roles)],
                    [("is_access_via_link_hidden", "=", False)],
                    [
                        (
                            "folder_id",
                            "any",
                            self._direct_user_permission_domain(
                                ["view", "edit"], company_domains=company_domains
                            ),
                        )
                    ],
                ]
            )
        )

        result = direct_domain | link_via_parent_domain

        if searched_roles == ["view"]:
            result &= ~self._search_user_permission(
                "in", ["edit"], company_domains=company_domains, ignore_link=ignore_link
            )

        return result

    @api.model
    def _user_permission_domain_fields(self) -> list:
        return [
            "access_internal",
            "access_via_link",
            "active",
            "company_id",
            "folder_id",
            "is_access_via_link_hidden",
            "owner_id",
            "shortcut_document_id",
            "shortcut_document_owner_id",
        ]

    def _permission_company_domains(self) -> dict:
        every_company_ids = self.env.user.with_context(
            active_test=False
        ).company_ids.ids
        allowed_company_ids = self.env.companies.ids
        return {
            "other": Domain("company_id", "!=", False)
            & Domain("company_id", "not in", every_company_ids),
            "allowed_or_none": Domain(
                "company_id", "in", [False, *allowed_company_ids]
            ),
            "any_except_disabled_and_archived": Domain(
                "company_id", "in", allowed_company_ids
            )
            | Domain("company_id", "not in", every_company_ids),
        }

    def _direct_user_permission_domain(
        self,
        searched_roles: list,
        exclude_ownership: bool = False,
        company_domains: dict | None = None,
        ignore_link: bool = False,
    ) -> Domain:
        company_domains = company_domains or self._permission_company_domains()
        other_company = company_domains["other"]
        allowed_or_no_company = company_domains["allowed_or_none"]
        any_except_disabled_and_archived_company = company_domains[
            "any_except_disabled_and_archived"
        ]

        if searched_roles == ["view"]:
            access_level_domain = Domain("role", "=", "view") & (
                Domain.TRUE
                if ignore_link
                else Domain("document_id.access_via_link", "in", ("none", "view"))
            )
            if not ignore_link:
                access_level_domain |= Domain("role", "=", False) & Domain(
                    "document_id.access_via_link", "=", "view"
                )
        elif searched_roles == ["edit"]:
            access_level_domain = Domain("role", "=", "edit")
            if not ignore_link:
                access_level_domain |= Domain(
                    "document_id.access_via_link", "=", "edit"
                )
        else:
            access_level_domain = Domain("role", "in", ("view", "edit"))
            if not ignore_link:
                access_level_domain |= Domain(
                    "document_id.access_via_link", "!=", "none"
                )
        access_domain = Domain(
            "access_ids",
            "any",
            Domain.AND(
                (
                    access_level_domain,
                    Domain("partner_id", "=", self.env.user.partner_id.id),
                    Domain("expiration_date", "=", False)
                    | Domain("expiration_date", ">", fields.Datetime.now()),
                )
            ),
        )

        if exclude_ownership:
            owner_domain = Domain.FALSE
        else:
            owner_domain = Domain("owner_id", "=", self.env.user.id) & Domain.OR(
                [
                    [("shortcut_document_id", "=", False)],
                    [("shortcut_document_owner_id", "=", self.env.user.id)],
                    self._direct_user_permission_domain(
                        ["view"],
                        exclude_ownership=True,
                        company_domains=company_domains,
                        ignore_link=ignore_link,
                    )
                    if set(searched_roles) == {"edit"}
                    else Domain.FALSE,
                ]
            )
        direct_domain = any_except_disabled_and_archived_company & (
            access_domain
            if "edit" not in searched_roles
            else access_domain | owner_domain
        )

        if self.env.user.has_group("document.group_documents_manager"):
            if searched_roles == ["view"]:
                direct_domain &= Domain("access_internal", "=", "none") | other_company
            else:
                direct_domain |= (
                    Domain("access_internal", "in", ("view", "edit"))
                    & allowed_or_no_company
                )
        elif not self.env.user.share:
            if searched_roles == ["view"]:
                internal_domain = Domain("access_internal", "=", "view")
                if not ignore_link:
                    internal_domain &= Domain("access_via_link", "in", ("none", "view"))
            elif searched_roles == ["edit"]:
                internal_domain = Domain("access_internal", "=", "edit")
                if not ignore_link:
                    internal_domain |= Domain("access_internal", "=", "view") & Domain(
                        "access_via_link", "=", "edit"
                    )
            else:
                internal_domain = Domain("access_internal", "in", ("view", "edit"))
            direct_domain |= internal_domain & allowed_or_no_company

        return direct_domain

    def _is_download_allowed(self) -> bool:
        self.check_singleton()
        target = self.shortcut_document_id or self
        allowed = not target.is_download_blocked or (
            target.user_permission == "edit" or target.access_via_link == "edit"
        )
        # Log the INPUTS, not only the refusal. Both of these gates used to be
        # visible in a log only through the caller's `content_refused` event,
        # so an allowed request said nothing -- and "was this blocked document
        # served because the block is off, because the caller is an editor, or
        # because the link is an edit link?" was unanswerable from any log,
        # which is exactly the question a download-block complaint asks.
        _debug.logic(
            "download_gate",
            document=self,
            target=target,
            allowed=allowed,
            blocked=target.is_download_blocked,
            permission=target.user_permission,
            via_link=target.access_via_link,
        )
        return allowed

    def _is_inline_content_allowed(self) -> bool:
        self.check_singleton()
        if self._is_download_allowed():
            return True
        target = self.shortcut_document_id or self
        renderable = is_mimetype_inline_rendered(target.mimetype)
        _debug.logic(
            "inline_gate",
            document=self,
            target=target,
            allowed=renderable,
            mimetype=target.mimetype or "",
        )
        return renderable

    def action_update_access_rights(
        self,
        access_internal: str | None = None,
        access_via_link: str | None = None,
        is_access_via_link_hidden: bool | None = None,
        partners: dict | None = None,
        no_propagation: bool = False,
        is_download_blocked: bool | None = None,
    ) -> list | None:
        if len(self.ids) == 0:
            return None
        self._check_access_or_raise(
            "write", self.env._("You are not allowed to update these access rights.")
        )

        if self.shortcut_document_id:
            _debug.logic("access_update_refused", reason="shortcut", documents=self)
            raise UserError(
                _(
                    "You can not update the access of a shortcut, update its target instead."
                )
            )

        access_options = {"view", "edit", "none", None}
        hidden_options = {None, True, False}
        role_options = {"edit", "view", False, None}
        incorrect_fields_to_options = {
            **(
                {"is_access_via_link_hidden": hidden_options}
                if is_access_via_link_hidden not in hidden_options
                else {}
            ),
            **(
                {"is_download_blocked": hidden_options}
                if is_download_blocked not in hidden_options
                else {}
            ),
            **(
                {"access_via_link": access_options}
                if access_via_link not in access_options
                else {}
            ),
            **(
                {"access_internal": access_options}
                if access_internal not in access_options
                else {}
            ),
            **(
                {"partners.role": role_options}
                if any(
                    role not in role_options for (role, __) in (partners or {}).values()
                )
                else {}
            ),
        }
        if incorrect_fields_to_options:
            _debug.logic(
                "access_update_refused",
                reason="bad_values",
                fields=sorted(incorrect_fields_to_options),
            )
            hints = "\n- " + "\n- ".join(
                f"{name}: {options}"
                for name, options in incorrect_fields_to_options.items()
            )
            raise UserError(
                _(
                    "Incorrect values. Use one of the following for the following fields: %(hints)s.)",
                    hints=hints,
                )
            )

        member_changes = None
        if partners:
            partners = {
                self.env["res.partner"].browse(int(partner))
                if isinstance(partner, str | int)
                else partner: (
                    role,
                    fields.Datetime.to_datetime(exp)
                    if exp and isinstance(exp, str)
                    else exp,
                )
                for partner, (role, exp) in (partners or {}).items()
            }
            _debug.pipeline(
                "access_members_update",
                documents=self,
                partners=len(partners),
                propagate=not no_propagation,
            )
            member_changes = self._action_update_members(
                partners, no_propagation=no_propagation
            )

        changes_by_document_dict = self._action_update_access(
            access_internal,
            access_via_link,
            is_access_via_link_hidden,
            no_propagation=no_propagation,
            is_download_blocked=is_download_blocked,
        )
        if member_changes:
            created_or_updated_access, removed_access = member_changes
            self._update_changes_by_document_dict(
                created_or_updated_access, removed_access, changes_by_document_dict
            )

        self.env["document.access.tracking"]._create_access_tracking(
            changes_by_document_dict
        )
        _debug.lifecycle(
            "access_rights_updated",
            documents=self,
            changed=len(changes_by_document_dict),
        )

        return self.mapped("user_permission")

    def _action_update_access(
        self,
        access_internal: str | None,
        access_via_link: str | None,
        is_access_via_link_hidden: bool | None,
        no_propagation: bool = False,
        is_download_blocked: bool | None = None,
    ) -> dict:
        self.flush_model()
        changes_by_document_dict = defaultdict(dict)
        for field, value in (
            ("access_internal", access_internal),
            ("access_via_link", access_via_link),
            ("is_access_via_link_hidden", is_access_via_link_hidden),
            ("is_download_blocked", is_download_blocked),
        ):
            if value is None:
                continue

            skip_propagation = no_propagation or field == "is_access_via_link_hidden"
            _debug.pipeline("access_field_update", field=field, skip=skip_propagation)

            candidates_domain = Domain(
                [
                    ("shortcut_document_id", "=", False),
                    ("id", "in" if skip_propagation else "child_of", self.ids),
                ]
            )
            candidates_domain &= self._get_domain_access_update()
            candidates_query = self.with_context(active_test=False)._search(
                candidates_domain
            )

            candidates = candidates_query.select(
                *(
                    self._field_to_sql(candidates_query.table, fname, candidates_query)
                    for fname in ("id", "folder_id", "shortcut_document_id", field)
                )
            )

            self.env.cr.execute(
                SQL(
                    """
                WITH RECURSIVE candidates AS (%(candidates)s),
                -- explore the folders
                documents_to_update AS (
                    SELECT id, %(field)s
                      FROM candidates
                     WHERE id = ANY(%(root_ids)s)
                     UNION
                    SELECT child.id, child.%(field)s
                      FROM candidates AS child
                      JOIN documents_to_update AS parent
                        ON child.folder_id = parent.id
                ),
                -- document.shortcut_ids are updated in "SUDO" to stay in sync
                documents_and_shortcuts AS (%(documents_and_shortcuts)s)
                    UPDATE document_document
                       SET %(field)s = %(value)s
                      FROM documents_and_shortcuts AS doc
                        -- document | document.children_ids | document.shortcut_ids
                     WHERE document_document.id = doc.id
                       -- only rows that actually change: no needless write, and
                       -- tracking is returned the old value of a real change
                       AND document_document.%(field)s IS DISTINCT FROM %(value)s
                 RETURNING doc.id, doc.%(field)s
            """,
                    field=SQL.identifier(field),
                    value=value,
                    root_ids=self.ids,
                    candidates=candidates,
                    documents_and_shortcuts=self._shortcuts_union_sql(
                        "documents_to_update", ("id", field)
                    ),
                )
            )

            for id, old_value in self.env.cr.fetchall():
                changes_by_document_dict[id][field] = old_value
            _debug.perf.count("access_field_rows", field=field, value=value)

        self._invalidate_permission_cache(
            [
                "access_internal",
                "access_via_link",
                "is_access_via_link_hidden",
                "is_download_blocked",
            ]
        )

        return changes_by_document_dict

    @api.model
    def _invalidate_permission_cache(self, fields_written: list[str]) -> None:
        # The SQL above bypasses `modified()`, so every non-stored compute
        # that reads `user_permission` (user_folder_id, user_can_move,
        # display_name, ...) has to be dropped by hand along with it.
        permission = self._fields["user_permission"]
        dependents = [
            field.name
            for field in self.pool.get_dependent_fields(permission)
            if field.model_name == self._name and not field.store
        ]
        _debug.pipeline(
            "permission_cache_invalidated",
            written=fields_written,
            dependents=len(dependents),
        )
        self.invalidate_model([*fields_written, "user_permission", *dependents])

    def _get_permission_without_token(self) -> str:
        self.check_singleton()
        return self._get_permission_without_token_multi()[self]

    def _get_permission_without_token_multi(self) -> dict:
        permission_by_document = dict.fromkeys(self, "none")
        saved = self.filtered(lambda document: isinstance(document.id, int))
        if not saved:
            return permission_by_document

        self.flush_model(self._user_permission_domain_fields())
        self.env["document.access"].flush_model(
            ["document_id", "partner_id", "role", "expiration_date"]
        )
        documents_sudo = (
            self.env["document.document"].sudo().with_context(active_test=False)
        )
        in_scope = Domain("id", "in", saved.ids)
        company_domains = self._permission_company_domains()
        levels = {}
        for level in ("view", "edit"):
            query = documents_sudo._search(
                in_scope
                & self._search_user_permission(
                    "in",
                    [level],
                    company_domains=company_domains,
                    ignore_link=True,
                )
            )
            levels.update(dict.fromkeys(query.get_result_ids(), level))
        _debug.perf.count(
            "permission_without_token", documents=saved, resolved=len(levels)
        )
        for document in saved:
            permission_by_document[document] = levels.get(document.id, "none")
        return permission_by_document

    def _get_unauthorized_root_document_owners_sudo(self) -> models.Model:
        return self.mapped("owner_id").sudo().filtered("share")

    def _prepare_inherited_access_vals(self) -> list[dict]:
        self.check_singleton()
        vals = [
            {
                "partner_id": access.partner_id.id,
                "role": access.role,
                "expiration_date": access.expiration_date,
            }
            for access in self.access_ids.filtered("role")
            if access.partner_id != self.owner_id.partner_id
        ]
        if self.owner_id:
            vals += [{"partner_id": self.owner_id.partner_id.id, "role": "edit"}]
        return vals

    @api.model
    def _validated_create_access_commands(self, access_ids: Any) -> list:
        commands = list(access_ids or [])
        for command in commands:
            code = command[0] if isinstance(command, list | tuple) else command
            if code in (Command.CREATE, Command.CLEAR):
                continue
            if code == Command.SET and not command[2]:
                continue
            _debug.logic("access_command_refused", code=code)
            raise UserError(
                _(
                    "Document access can only be granted at creation "
                    "(Command.create) or cleared; got command %s.",
                    code,
                )
            )
        return commands

    def _cannot_create_sibling(self) -> bool:
        self.check_singleton()
        if self.env.su:
            return False
        if self.folder_id:
            return self.folder_id.user_permission != "edit"
        return (
            not self.env.user.has_group("document.group_documents_manager")
            and self.owner_id != self.env.user
        )

    def _is_company_root_folder(self) -> bool:
        self.check_singleton()
        return self.type == "folder" and not self.folder_id and not self.owner_id

    @api.model
    def _archive_denied_message(self) -> str:
        return _("You do not have sufficient access rights to delete these documents.")

    def _raise_if_unauthorized_archive(self) -> None:
        if self.env.su:
            return
        unowned_documents = self.filtered(
            lambda d: d.active and d.owner_id != self.env.user
        )
        if any(
            folder.user_permission != "edit" for folder in unowned_documents.folder_id
        ):
            _debug.logic(
                "archive_refused",
                reason="unowned_in_uneditable_folder",
                documents=unowned_documents,
            )
            raise UserError(self._archive_denied_message())
