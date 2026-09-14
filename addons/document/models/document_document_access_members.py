from collections import defaultdict
from typing import Any

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    # The member (partner role) side of access: propagation targets, the
    # shortcut union every UPDATE joins on, and the company sync that rides
    # the same SQL shape.

    def _action_update_members(
        self, partners: dict, no_propagation: bool = False
    ) -> tuple:
        self.env["document.access"].flush_model()

        partners_to_remove = self.env["res.partner"]
        values_to_update = defaultdict(lambda: self.env["res.partner"])

        for partner, (role, expiration_date) in partners.items():
            if role is False:
                partners_to_remove |= partner
            elif role is not None or expiration_date is not None:
                values_to_update[role, expiration_date] |= partner

        documents = self._propagation_target_select(
            no_propagation=no_propagation, access=True
        )
        _debug.pipeline(
            "members_update_plan",
            documents=self,
            to_remove=len(partners_to_remove),
            role_groups=len(values_to_update),
            propagate=not no_propagation,
        )

        created_or_updated_access = []
        for (role, expiration_date), role_partners in values_to_update.items():
            if role is None:
                created_or_updated_access += self._update_members_expiration(
                    documents, role_partners, expiration_date
                )
                continue

            update_fields = [SQL("role = %(role)s", role=role)]
            if expiration_date is not None:
                update_fields.append(
                    SQL(
                        "expiration_date = %(expiration_date)s",
                        expiration_date=expiration_date or None,
                    )
                )
            update_fields = SQL(",").join(update_fields)

            self.env.cr.execute(
                SQL(
                    """
                    WITH documents AS (%(documents)s),
                         documents_and_shortcuts AS (%(documents_and_shortcuts)s),
                    existing AS (
                        SELECT document_id, partner_id, role, expiration_date
                          FROM document_access
                          JOIN documents_and_shortcuts
                            ON document_id = documents_and_shortcuts.id
                           AND partner_id = any(%(partner_ids)s)
                    ),
                    updated_or_created AS (
                        INSERT INTO document_access (
                                document_id,
                                partner_id,
                                role,
                                expiration_date
                        ) (
                            SELECT DISTINCT ON (doc.id, partner_id) doc.id,
                                   partner_id,
                                   %(role)s,
                                   %(expiration_date)s
                              FROM documents_and_shortcuts AS doc
                      JOIN LATERAL UNNEST(%(partner_ids)s) AS partner_id ON TRUE
                        )
                       ON CONFLICT (document_id, partner_id) DO UPDATE SET %(update_fields)s
                         RETURNING document_id, partner_id, role, expiration_date
                    )
                    SELECT 'existing' as action, * FROM existing
                    UNION ALL
                    SELECT 'upsert' as action, * FROM updated_or_created
                    ORDER BY action ASC
                """,
                    documents=documents,
                    documents_and_shortcuts=self._shortcuts_union_sql("documents"),
                    partner_ids=role_partners.ids,
                    expiration_date=expiration_date or None,
                    role=role,
                    update_fields=update_fields,
                )
            )
            created_or_updated_access += self.env.cr.fetchall()
            _debug.perf.count(
                "members_upserted", role=role, partners=len(role_partners)
            )

        removed_access = []
        if partners_to_remove:
            self.env.cr.execute(
                SQL(
                    """
                WITH documents AS (%(documents)s),
                     documents_and_shortcuts AS (%(documents_and_shortcuts)s)
                DELETE FROM document_access AS access
                      USING documents_and_shortcuts AS doc
                      WHERE access.document_id = doc.id
                        AND access.partner_id = ANY(%(partner_ids)s)
                  RETURNING access.document_id, access.partner_id
            """,
                    documents=documents,
                    documents_and_shortcuts=self._shortcuts_union_sql("documents"),
                    partner_ids=partners_to_remove.ids,
                )
            )
            removed_access = self.env.cr.fetchall()
            _debug.perf.count("members_removed", rows=len(removed_access))

        self._invalidate_permission_cache(["access_ids"])
        self.env["document.access"].invalidate_model()

        return created_or_updated_access, removed_access

    def _update_members_expiration(
        self, documents: SQL, partners: models.Model, expiration_date: Any
    ) -> list:
        # A role of None leaves the member's role alone, so there is nothing
        # to insert: only rows that already carry a role move. The rows are
        # reported in the same (action, document, partner, role, expiration)
        # shape as the upsert so tracking reads them as updates.
        self.env.cr.execute(
            SQL(
                """
                WITH documents AS (%(documents)s),
                     documents_and_shortcuts AS (%(documents_and_shortcuts)s),
                existing AS (
                    SELECT access.id, document_id, partner_id, role, expiration_date
                      FROM document_access AS access
                      JOIN documents_and_shortcuts
                        ON document_id = documents_and_shortcuts.id
                       AND partner_id = any(%(partner_ids)s)
                     WHERE role IS NOT NULL
                ),
                updated AS (
                    UPDATE document_access AS access
                       SET expiration_date = %(expiration_date)s
                      FROM existing
                     WHERE access.id = existing.id
                 RETURNING access.document_id, access.partner_id, access.role,
                           access.expiration_date
                )
                SELECT 'existing' AS action, document_id, partner_id, role,
                       expiration_date
                  FROM existing
                 UNION ALL
                SELECT 'upsert' AS action, * FROM updated
                 ORDER BY action ASC
                """,
                documents=documents,
                documents_and_shortcuts=self._shortcuts_union_sql("documents"),
                partner_ids=partners.ids,
                expiration_date=expiration_date or None,
            )
        )
        return self.env.cr.fetchall()

    @api.model
    def _add_user_role_without_propagation(
        self, role: str, documents_per_user: dict
    ) -> None:
        existing_access = (
            self.env["document.access"]
            .sudo()
            .search(
                Domain.OR(
                    [
                        ("partner_id", "=", owner.partner_id.id),
                        ("document_id", "in", documents.ids),
                    ]
                    for owner, documents in documents_per_user.items()
                )
            )
        )
        _debug.lifecycle(
            "owner_role_kept",
            role=role,
            users=len(documents_per_user),
            existing=len(existing_access),
        )
        existing_access.role = role
        existing_access_values = {
            (a.partner_id, a.document_id) for a in existing_access
        }
        self.env["document.access"].sudo().create(
            [
                {
                    "partner_id": owner.partner_id.id,
                    "document_id": document.id,
                    "role": role,
                }
                for owner, documents in documents_per_user.items()
                for document in documents
                if (owner.partner_id, document) not in existing_access_values
            ]
        )

    def _propagation_target_select(
        self, extra: Domain = Domain.TRUE, *, no_propagation: bool = False, access: bool
    ) -> SQL:
        domain = Domain.AND(
            (
                extra,
                Domain("shortcut_document_id", "=", False),
                Domain("id", "in" if no_propagation else "child_of", self.ids),
                self._get_domain_access_update()
                if access
                else self._get_domain_propagation(),
            )
        )
        return self.with_context(active_test=False)._search(domain).select()

    def _get_domain_propagation(self) -> Domain:
        return Domain.TRUE if self.env.su else Domain("user_permission", "=", "edit")

    def _get_domain_access_update(self) -> Domain:
        return self._get_domain_propagation()

    @api.model
    def _shortcuts_union_sql(
        self, source: str, columns: tuple[str, ...] = ("id",), *, include: bool = True
    ) -> SQL:
        projection = SQL(", ").join(SQL.identifier(column) for column in columns)
        base = SQL("SELECT %s FROM %s", projection, SQL.identifier(source))
        if not include:
            return base
        return SQL(
            """%s
                     UNION
                    SELECT %s
                      FROM document_document AS shortcut
                      JOIN %s AS shortcut_target
                        ON shortcut_target.id = shortcut.shortcut_document_id""",
            base,
            SQL(", ").join(SQL.identifier("shortcut", column) for column in columns),
            SQL.identifier(source),
        )

    @api.model
    def _update_changes_by_document_dict(
        self,
        created_or_updated_access: list,
        removed_access: list,
        changes_by_document_dict: dict,
    ) -> None:
        old_values = defaultdict(dict)
        for action, doc, partner, role, exp in created_or_updated_access:
            exp = fields.Date.to_string(exp) or "None"
            partner_dict = changes_by_document_dict.setdefault(doc, {}).setdefault(
                "members", {"added": {}, "updated": {}, "removed": []}
            )
            if action == "upsert":
                if old := old_values[doc].get(partner):
                    partner_dict["updated"][partner] = {
                        "role": (old["role"], role),
                        "expiration_date": (old["expiration_date"], exp),
                    }
                else:
                    partner_dict["added"][partner] = {
                        "role": role,
                        "expiration_date": exp,
                    }
            elif action == "existing":
                old_values[doc][partner] = {
                    "role": role,
                    "expiration_date": exp,
                }
        for doc, partner in removed_access:
            (
                changes_by_document_dict.setdefault(doc, {})
                .setdefault("members", {"added": {}, "updated": {}, "removed": []})[
                    "removed"
                ]
                .append(partner)
            )

    def _update_company(self, company_id: int | bool) -> None:
        self.flush_model()
        to_update = self._propagation_target_select(
            Domain("id", "in", self.ids) | Domain("company_id", "!=", company_id),
            access=False,
        )
        self.env.cr.execute(
            SQL(
                """
                    WITH documents_to_update AS (%(to_update)s),
                    documents_and_shortcuts AS (%(documents_and_shortcuts)s)
                    UPDATE document_document
                       SET %(field)s = %(value)s
                      FROM documents_and_shortcuts AS doc
                     WHERE document_document.id = doc.id
                """,
                field=SQL("company_id"),
                value=company_id or None,
                to_update=to_update,
                documents_and_shortcuts=self._shortcuts_union_sql(
                    "documents_to_update", include=bool(company_id)
                ),
            )
        )
        _debug.pipeline(
            "company_propagated",
            documents=self,
            company=company_id,
            rows=self.env.cr.rowcount,
        )

        self._invalidate_permission_cache(["company_id"])
