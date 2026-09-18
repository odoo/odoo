from collections import OrderedDict
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.document.tools import UserFolder

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    def _search_last_access_date_group(
        self, operator: str, operand: list | set
    ) -> list:
        if operator != "in":
            return NotImplemented
        values = set(operand)
        if False in values:
            query = SQL(
                "(%s SELECT document_id FROM last_access_date)",
                self._get_last_access_date_group_cte(),
            )
            no_access_date = [("id", "not in", query)]
            if len(values) > 1:
                values.remove(False)
                return [
                    "|",
                    *no_access_date,
                    *self._search_last_access_date_group(operator, values),
                ]
            return no_access_date
        query = SQL(
            """(%s SELECT document_id FROM last_access_date WHERE date = ANY(%s))""",
            self._get_last_access_date_group_cte(),
            list(values),
        )
        return [("id", "in", query)]

    @api.depends("access_ids", "access_ids.last_access_date")
    @api.depends_context("uid")
    def _compute_last_access_date_group(self) -> None:
        self.env["document.access"].flush_model(["last_access_date"])
        self.env.cr.execute(
            SQL(
                """(%s SELECT document_id, date FROM last_access_date WHERE document_id = ANY(%s))""",
                self._get_last_access_date_group_cte(),
                self.ids,
            )
        )
        values = {
            line["document_id"]: line["date"] for line in self.env.cr.dictfetchall()
        }
        for document in self:
            document.last_access_date_group = values.get(document.id)

    def _last_access_date_group_sql(
        self, field: fields.Field, alias: str, query: Any = None
    ) -> SQL:
        if query is None:
            msg = (
                "last_access_date_group needs a query to hang its join on; "
                "it cannot be rendered as a standalone expression"
            )
            raise ValueError(msg)
        join_alias = f"{alias}__last_access"
        subquery = SQL(
            """(SELECT document_id,
                %s AS date_group
                FROM document_access
                WHERE partner_id = %s)""",
            self._last_access_date_group_case_sql(),
            self.env.user.partner_id.id,
        )
        condition = SQL(
            "%s = %s",
            SQL.identifier(join_alias, "document_id"),
            SQL.identifier(alias, "id"),
        )
        query.add_join("LEFT JOIN", join_alias, subquery, condition)
        return SQL.identifier(join_alias, "date_group")

    def _get_last_access_date_group_cte(self) -> SQL:
        return SQL(
            """
            WITH last_access_date AS (
                SELECT %s AS date,
                       document_id
                  FROM document_access
                 WHERE partner_id = %s
            )
        """,
            self._last_access_date_group_case_sql(),
            self.env.user.partner_id.id,
        )

    @api.model
    def _get_fields_search_panel(self) -> list:
        search_panel_fields = [
            "access_internal",
            "access_token",
            "access_via_link",
            "active",
            "company_id",
            "description",
            "display_name",
            "user_folder_id",
            "is_access_via_link_hidden",
            "is_user_favorite",
            "mail_alias_domain_count",
            "owner_id",
            "shortcut_document_id",
            "user_permission",
        ]
        if not self.env.user.share:
            search_panel_fields += [
                "alias_domain_id",
                "alias_email",
                "alias_name",
                "alias_tag_ids",
                "create_activity_type_id",
                "create_activity_user_id",
                "partner_id",
            ]
        return search_panel_fields

    def _last_access_date_group_case_sql(self) -> SQL:
        now = fields.Datetime.now()
        return SQL(
            """(CASE
                   WHEN last_access_date > %s THEN '3_day'
                   WHEN last_access_date > %s THEN '2_week'
                   WHEN last_access_date > %s THEN '1_month'
                   ELSE '0_older'
               END)""",
            now - relativedelta(days=1),
            now - relativedelta(days=7),
            now - relativedelta(months=1),
        )

    def _order_by_sql_last_access_date_group(
        self, field, alias: str, direction: SQL, nulls: SQL, query: Any
    ) -> SQL:
        sql_field = SQL(
            "(SELECT last_access_date FROM document_access WHERE partner_id = %s AND document_id = %s)",
            self.env.user.partner_id.id,
            SQL.identifier(alias, "id"),
        )
        return self._order_value_to_sql(sql_field, direction, nulls, query)

    @api.model
    def _search_panel_get_folder_counts(self, model_domain: Domain) -> dict:
        with _debug.perf("search_panel_folder_counts", cr=self.env.cr):
            return {
                folder.id: count
                for folder, count in self._read_group(
                    model_domain & Domain("folder_id", "!=", False),
                    groupby=["folder_id"],
                    aggregates=["__count"],
                )
            }

    @api.model
    def _search_panel_rollup_folder_counts(self, values_range: dict) -> None:
        parent_by_folder = {
            folder.id: folder.folder_id.id for folder in self.browse(values_range)
        }
        local_counts = {
            folder_id: values["__count"] for folder_id, values in values_range.items()
        }
        _debug.pipeline("search_panel_rollup", folders=len(values_range))
        for folder_id, count in local_counts.items():
            if not count:
                continue
            seen = {folder_id}
            parent_id = parent_by_folder.get(folder_id)
            while parent_id and parent_id not in seen:
                seen.add(parent_id)
                if parent_id in values_range:
                    values_range[parent_id]["__count"] += count
                parent_id = parent_by_folder.get(parent_id)

    @api.model
    def search_panel_select_range(self, field_name: str, **kwargs) -> dict:

        def convert_user_folder_ids_to_int(vals: dict) -> None:
            user_folder = self._parse_user_folder(vals["user_folder_id"])
            if user_folder is not None and user_folder.is_folder:
                vals["user_folder_id"] = user_folder.folder_id

        if field_name == "user_folder_id":
            enable_counters = kwargs.get("enable_counters", False)
            search_panel_fields = self._get_fields_search_panel()
            domain = Domain("type", "=", "folder")

            _debug.pipeline("search_panel_range", counters=enable_counters)
            if unique_folder_id := self.env.context.get("documents_unique_folder_id"):
                values = self.env["document.document"].search_read(
                    domain & Domain("folder_id", "child_of", unique_folder_id),
                    search_panel_fields,
                )
                for record in values:
                    convert_user_folder_ids_to_int(record)
                    if record["id"] == unique_folder_id:
                        record["user_folder_id"] = False
                return {
                    "parent_field": "user_folder_id",
                    "values": values,
                }

            records = self.env["document.document"].search_read(
                domain, search_panel_fields
            )
            alias_tag_data = {}
            if not self.env.user.share:
                alias_tag_ids = {
                    alias_tag_id
                    for rec in records
                    for alias_tag_id in rec["alias_tag_ids"]
                }
                alias_tag_data = {
                    alias_tag["id"]: {
                        "id": alias_tag.id,
                        "color": alias_tag.color,
                        "display_name": alias_tag.display_name,
                    }
                    for alias_tag in self.env["document.tag"].browse(alias_tag_ids)
                }
            local_counts = {}
            if enable_counters:
                model_domain = Domain.AND(
                    [
                        kwargs.get("search_domain", []),
                        kwargs.get("category_domain", []),
                        kwargs.get("filter_domain", []),
                    ]
                )
                local_counts = self._search_panel_get_folder_counts(model_domain)

            targets = self.browse(
                r["shortcut_document_id"][0]
                for r in records
                if r["shortcut_document_id"]
            )
            targets_user_permission = {t.id: t.user_permission for t in targets}

            values_range = OrderedDict()
            for record in records:
                record_id = record["id"]
                convert_user_folder_ids_to_int(record)
                if not self.env.user.share:
                    record["alias_tag_ids"] = [
                        alias_tag_data[tag_id] for tag_id in record["alias_tag_ids"]
                    ]
                if enable_counters:
                    record["__count"] = local_counts.get(record_id, 0)
                if record["shortcut_document_id"]:
                    record["target_user_permission"] = targets_user_permission[
                        record["shortcut_document_id"][0]
                    ]
                values_range[record_id] = record

            if enable_counters:
                self._search_panel_rollup_folder_counts(values_range)

            special_roots = []
            if not self.env.user.share:
                special_roots = [
                    {
                        "bold": True,
                        "childrenIds": [],
                        "parentId": False,
                        "user_permission": "edit",
                    }
                    | values
                    for values in [
                        {
                            "display_name": _("Company"),
                            "id": UserFolder.COMPANY,
                            "description": _("Common roots for all company users."),
                            "user_permission": "edit"
                            if self.env.user.has_group(
                                "document.group_documents_manager"
                            )
                            else "view",
                        },
                        {
                            "display_name": _("My Drive"),
                            "id": UserFolder.MY,
                            "user_permission": "edit",
                            "description": _("Your individual space."),
                        },
                        {
                            "display_name": _("Shared with me"),
                            "id": UserFolder.SHARED,
                            "description": _(
                                "Additional documents you have access to."
                            ),
                        },
                        {
                            "display_name": _("Recent"),
                            "id": UserFolder.RECENT,
                            "description": _("Recently accessed documents."),
                        },
                    ]
                ]
                if not self.env.context.get("documents_search_panel_no_trash"):
                    special_roots.append(
                        {
                            "display_name": _("Trash"),
                            "id": UserFolder.TRASH,
                            "description": _(
                                "Items in trash will be deleted forever after %s days.",
                                self.get_deletion_delay(),
                            ),
                        }
                    )

            return {
                "parent_field": "user_folder_id",
                "values": list(values_range.values()) + special_roots,
            }

        return super().search_panel_select_range(field_name, **kwargs)
