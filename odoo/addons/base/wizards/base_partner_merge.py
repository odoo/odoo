import datetime
import logging
from ast import literal_eval
from typing import Any

from odoo import api, fields, models
from odoo.db import FunctionStatus
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.libs.text import name_length_band, similarity_ratio
from odoo.tools import SQL

_logger = logging.getLogger("odoo.addons.base.partner.merge")
_debug = DebugLog(__name__)

SIMILAR_NAME_PAIR_BATCH = 5000


class BasePartnerMergeLine(models.TransientModel):
    _name = "base.partner.merge.line"

    _description = "Merge Partner Line"
    _order = "min_id asc"

    wizard_id = fields.Many2one(comodel_name="base.partner.merge.automatic.wizard")
    min_id = fields.Integer(string="MinID")
    aggr_ids = fields.Char(
        string="Ids",
        required=True,
    )


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _name = "base.partner.merge.automatic.wizard"
    _inherit = ["mixin.merge"]
    _description = "Merge Partner Wizard"

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        active_ids = self.env.context.get("active_ids")
        if self.env.context.get("active_model") == "res.partner" and active_ids:
            if "state" in fields:
                res["state"] = "selection"
            if "partner_ids" in fields:
                res["partner_ids"] = [Command.set(active_ids)]
            if "dst_partner_id" in fields:
                res["dst_partner_id"] = self._get_ordered_partner(active_ids)[-1].id
        return res

    group_by_email = fields.Boolean(string="Email")
    group_by_name = fields.Boolean(string="Name")
    group_by_is_company = fields.Boolean(string="Is Company")
    group_by_vat = fields.Boolean(string="VAT")
    group_by_parent_id = fields.Boolean(string="Parent Company")
    match_similar_names = fields.Boolean(
        string="Similar Names",
        help="Also group contacts whose names differ slightly, such as "
        "'Acme Corp' and 'ACME Corporation'. The exact criteria above can only "
        "match names that are already identical.",
    )

    state = fields.Selection(
        selection=[
            ("option", "Option"),
            ("selection", "Selection"),
            ("finished", "Finished"),
        ],
        default="option",
        readonly=True,
        required=True,
    )

    number_group = fields.Integer(
        string="Group of Contacts",
        readonly=True,
    )
    current_line_id = fields.Many2one(comodel_name="base.partner.merge.line")
    line_ids = fields.One2many(
        comodel_name="base.partner.merge.line",
        inverse_name="wizard_id",
        string="Lines",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Contacts",
        context={"active_test": False},
    )
    dst_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destination Contact",
    )

    exclude_contact = fields.Boolean(string="A user associated to the contact")
    exclude_journal_item = fields.Boolean(
        string="Journal Items associated to the contact"
    )
    maximum_group = fields.Integer(string="Maximum of Group of Contacts")
    absorb_source_values = fields.Boolean(
        default=True,
        help="Fill the destination's empty fields from the contacts merged into "
        "it. Turn it off to keep the destination's own identity, which is what a "
        "catch-all contact needs.",
    )

    _MERGE_SIZE_LIMIT = 3
    _IDENTIFYING_GROUPBY_FIELDS = frozenset({"email", "name", "vat"})

    def _is_source_absorbed_on_merge(self) -> bool:
        return not self or self.absorb_source_values

    def _get_merge_tables_excluded(self, model: str) -> set[str]:
        tables = super()._get_merge_tables_excluded(model)
        if model == "res.partner":
            tables.add("res_partner_identifier")
            tables.add("res_partner_phone_number_rel")
            tables.add("res_partner_bank")
        return tables

    @api.model
    def _update_foreign_keys(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        self._update_foreign_keys_generic("res.partner", src_partners, dst_partner)

    @api.model
    def _update_reference_fields(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        self._update_reference_fields_generic("res.partner", src_partners, dst_partner)

    def _get_fields_summable(self) -> list[str]:
        return []

    def _get_fields_excluded_value(self) -> tuple[str, ...]:
        return ()

    def _get_fields_deferred_value(self) -> tuple[str, ...]:
        return ("barcode",)

    @api.model
    def _update_values(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> dict[str, Any]:
        deferred_values = self._update_values_generic(
            src_partners,
            dst_partner,
            summable_fields=self._get_fields_summable(),
            deferred_fields=("parent_id", *self._get_fields_deferred_value()),
            excluded_fields=self._get_fields_excluded_value(),
        )
        parent_id = deferred_values.pop("parent_id", None)
        if parent_id and parent_id != dst_partner.id:
            try:
                dst_partner.write({"parent_id": parent_id})
            except ValidationError:
                _logger.info(
                    "Skip recursive partner hierarchies for parent_id %s of partner: %s",
                    parent_id,
                    dst_partner.id,
                )
                _debug.logic(
                    "merge_parent_skipped", partner=dst_partner.id, parent=parent_id
                )
        return deferred_values

    @api.model
    def _merge_bank_accounts(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        all_src_accounts = src_partners.bank_ids

        absorbed = 0  # debuglog
        for src_account in all_src_accounts:
            duplicate_account = dst_partner.bank_ids.filtered(
                lambda a, src_account=src_account: (
                    a.sanitized_acc_number == src_account.sanitized_acc_number
                )
            )
            if duplicate_account:
                self._update_foreign_keys_generic(
                    "res.partner.bank", src_account, duplicate_account
                )
                self._update_reference_fields_generic(
                    "res.partner.bank", src_account, duplicate_account
                )
                src_account.sudo().unlink()
                absorbed += 1  # debuglog
            else:
                src_account.sudo().write({"partner_id": dst_partner.id})
        _debug.pipeline(
            "merge_bank_accounts",
            dst=dst_partner.id,
            accounts=len(all_src_accounts),
            absorbed=absorbed,
        )

    @api.model
    def _merge_phone_numbers(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        src_partners = src_partners.with_context(active_test=False)
        # Capture the choice before unlinking source relations clears their preferences.
        preferred = (
            dst_partner.preferred_phone_id
            or src_partners.mapped("preferred_phone_id")[:1]
        )
        numbers = src_partners.phone_ids.sudo()
        _debug.pipeline("merge_phone_numbers", dst=dst_partner.id, numbers=len(numbers))
        if numbers:
            numbers.write(
                {
                    "partner_ids": [
                        *(Command.unlink(p.id) for p in src_partners),
                        Command.link(dst_partner.id),
                    ]
                }
            )

        if preferred and dst_partner.preferred_phone_id != preferred:
            dst_partner.preferred_phone_id = preferred

    @api.model
    def _merge_identifiers(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        held_types = set(dst_partner.identifier_ids.type_id.ids)
        held_values = {
            (i.type_id.id, i.normalized_value) for i in dst_partner.identifier_ids
        }
        for src_identifier in src_partners.identifier_ids:
            identifier_type = src_identifier.type_id
            if identifier_type.multiple_per_contact:
                clash = (
                    identifier_type.id,
                    src_identifier.normalized_value,
                ) in held_values
            else:
                clash = identifier_type.id in held_types
            if clash:
                src_identifier.sudo().unlink()
                _debug.logic(
                    "merge_identifier_dropped",
                    dst=dst_partner.id,
                    type=identifier_type.code,
                )
            else:
                src_identifier.sudo().write({"partner_id": dst_partner.id})
                held_types.add(identifier_type.id)
                held_values.add((identifier_type.id, src_identifier.normalized_value))

    def _merge(
        self,
        partner_ids: list[int],
        dst_partner: models.BaseModel | None = None,
        extra_checks: bool = True,
    ) -> None:
        if self.env.is_admin():
            extra_checks = False

        Partner = self.env["res.partner"]
        partner_ids = Partner.browse(partner_ids).exists()
        if len(partner_ids) < 2:
            return

        selected = set(partner_ids.ids)
        for partner in partner_ids:
            ancestor = partner.parent_id
            while ancestor:
                if ancestor.id in selected:
                    raise UserError(
                        self.env._("You cannot merge a contact with one of his parent.")
                    )
                ancestor = ancestor.parent_id

        if len(partner_ids.with_context(active_test=False).user_ids) > 1:
            raise UserError(
                self.env._(
                    "You cannot merge contacts linked to more than one user even if only one is active."
                )
            )

        if extra_checks and len({partner.email for partner in partner_ids}) > 1:
            raise UserError(
                self.env._(
                    "All contacts must have the same email. Only the Administrator can merge contacts with different emails."
                )
            )

        if dst_partner and dst_partner in partner_ids:
            src_partners = partner_ids - dst_partner
        else:
            ordered_partners = self._get_ordered_partner(partner_ids.ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)
        _debug.pipeline(
            "merge",
            destination=dst_partner.id,
            sources=src_partners.ids,
            absorb=self._is_source_absorbed_on_merge(),
            extra_checks=extra_checks,
        )

        if dst_partner.company_id:
            partner_ids.mapped("user_ids").sudo().write(
                {
                    "company_ids": [Command.link(dst_partner.company_id.id)],
                    "company_id": dst_partner.company_id.id,
                }
            )

        deferred_values = {}
        if self._is_source_absorbed_on_merge():
            self._merge_phone_numbers(src_partners, dst_partner)
            self._merge_bank_accounts(src_partners, dst_partner)
        self._merge_identifiers(src_partners, dst_partner)

        with _debug.perf(
            "merge_repoint",
            cr=self.env.cr,
            destination=dst_partner.id,
            sources=len(src_partners),
        ):
            self._update_foreign_keys(src_partners, dst_partner)
            self._update_reference_fields(src_partners, dst_partner)
        if self._is_source_absorbed_on_merge():
            deferred_values = self._update_values(src_partners, dst_partner)

        self.env.add_to_compute(dst_partner._fields["partner_share"], dst_partner)

        self._log_merge_operation(src_partners, dst_partner)

        src_partners.sudo().unlink()

        if deferred_values:
            dst_partner.write(deferred_values)

    def _log_merge_operation(
        self, src_partners: models.BaseModel, dst_partner: models.BaseModel
    ) -> None:
        _logger.info(
            "(uid = %s) merged the partners %r with %s",
            self.env.uid,
            src_partners.ids,
            dst_partner.id,
        )

    def _merge_duplicate_group(self, partner_ids: list[int]) -> None:
        dst_partner = self._get_ordered_partner(partner_ids)[-1]
        src_partners = [pid for pid in partner_ids if pid != dst_partner.id]
        chunk = self._MERGE_SIZE_LIMIT - 1
        _debug.pipeline(
            "merge_duplicate_group",
            dst=dst_partner.id,
            sources=len(src_partners),
            chunks=-(-len(src_partners) // chunk),
        )
        for start in range(0, len(src_partners), chunk):
            self._merge(
                src_partners[start : start + chunk] + [dst_partner.id],
                dst_partner=dst_partner,
            )

    _GROUPBY_ALLOWED_FIELDS = frozenset(
        {"email", "name", "vat", "is_company", "parent_id"}
    )

    @api.model
    def _generate_query(self, fields: list[str], maximum_group: int = 100) -> SQL:
        sql_fields = []
        for field in fields:
            if field not in self._GROUPBY_ALLOWED_FIELDS:
                raise ValueError(f"Field {field!r} is not allowed in merge grouping")
            col = SQL.identifier(field)
            if field in ("email", "name"):
                sql_fields.append(SQL("lower(%s)", col))
            elif field == "vat":
                sql_fields.append(SQL("replace(%s, ' ', '')", col))
            else:
                sql_fields.append(col)
        group_fields = SQL(", ").join(sql_fields)

        filters = [
            SQL("%s IS NOT NULL", SQL.identifier(field))
            for field in fields
            if field in ("email", "name", "vat")
        ]

        parts = [
            SQL("SELECT min(id), array_agg(id)"),
            SQL("FROM res_partner"),
        ]
        if filters:
            parts.append(SQL("WHERE %s", SQL(" AND ").join(filters)))
        parts.extend(
            [
                SQL("GROUP BY %s", group_fields),
                SQL("HAVING COUNT(*) >= 2"),
                SQL("ORDER BY min(id)"),
            ]
        )
        if maximum_group:
            parts.append(SQL("LIMIT %s", maximum_group))

        return SQL(" ").join(parts)

    def _get_similar_name_threshold(self) -> float:
        return self.env["res.partner"]._get_similar_name_threshold()

    def _get_similar_name_pairs(
        self, limit: int, after: tuple[int, int] = (0, 0)
    ) -> list[tuple[int, int]]:
        registry = self.env.registry
        if not registry.has_trigram:
            raise UserError(
                self.env._(
                    "Grouping by similar names needs the pg_trgm PostgreSQL "
                    "extension, which this database does not have."
                )
            )
        self.env["res.partner"].flush_model(["active", "complete_name"])

        self.env.cr.execute(
            SQL(
                "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
                str(self._get_recall_threshold()),
            )
        )

        left = SQL('left_partner."complete_name"')
        right = SQL('right_partner."complete_name"')
        if registry.has_unaccent == FunctionStatus.INDEXABLE:
            left, right = registry.unaccent(left), registry.unaccent(right)
        query = SQL(
            """
            SELECT left_partner.id, right_partner.id
              FROM res_partner AS left_partner
              JOIN res_partner AS right_partner
                ON right_partner.id > left_partner.id
               AND %s %% %s
             WHERE left_partner.active
               AND right_partner.active
               AND left_partner.complete_name IS NOT NULL
               AND right_partner.complete_name IS NOT NULL
               AND (left_partner.id, right_partner.id) > (%s, %s)
             ORDER BY left_partner.id, right_partner.id
             LIMIT %s
            """,
            left,
            right,
            after[0],
            after[1],
            limit,
        )
        with _debug.perf("similar_name_pairs", cr=self.env.cr, limit=limit) as span:
            self.env.cr.execute(query)  # noqa: E8501  built via SQL(), no user input
            pairs = self.env.cr.fetchall()
            span.set(pairs=len(pairs))
        return pairs

    def _get_recall_threshold(self) -> float:
        return self.env["res.partner"]._get_similar_name_recall_threshold()

    def _get_similar_name_groups(
        self, maximum_group: int = 100
    ) -> list[tuple[int, list[int]]]:
        threshold = self._get_similar_name_threshold()
        names: dict[int, str] = {}
        root: dict[int, int] = {}

        def find(node: int) -> int:
            while root.setdefault(node, node) != node:
                root[node] = root[root[node]]
                node = root[node]
            return node

        def clusters() -> dict[int, list[int]]:
            members: dict[int, list[int]] = {}
            for node in root:
                members.setdefault(find(node), []).append(node)
            return members

        after = (0, 0)
        boundary: int | None = None
        pair_count = 0
        while True:
            pairs = self._get_similar_name_pairs(SIMILAR_NAME_PAIR_BATCH, after)
            pair_count += len(pairs)
            unnamed = {pid for pair in pairs for pid in pair} - names.keys()
            if unnamed:
                partners = self.env["res.partner"].browse(unnamed)
                partners.fetch(["complete_name"])
                names.update((p.id, (p.complete_name or "").lower()) for p in partners)
            for left_id, right_id in pairs:
                left_name, right_name = names.get(left_id), names.get(right_id)
                if not left_name or not right_name:
                    continue
                shortest, longest = name_length_band(len(left_name), threshold)
                if not shortest <= len(right_name) <= longest:
                    continue
                if similarity_ratio(left_name, right_name) < threshold:
                    continue
                left_root, right_root = find(left_id), find(right_id)
                if left_root != right_root:
                    root[max(left_root, right_root)] = min(left_root, right_root)
            if len(pairs) < SIMILAR_NAME_PAIR_BATCH:
                boundary = None
                break
            after = pairs[-1]
            boundary = after[0]
            if (
                maximum_group
                and sum(
                    1
                    for members in clusters().values()
                    if len(members) >= 2 and max(members) < boundary
                )
                >= maximum_group
            ):
                break

        groups = [
            (min(members), sorted(members))
            for members in clusters().values()
            if len(members) >= 2 and (boundary is None or max(members) < boundary)
        ]
        groups.sort()
        _debug.pipeline(
            "similar_name_groups",
            pairs=pair_count,
            partners=len(names),
            threshold=threshold,
            groups=len(groups),
            maximum_group=maximum_group,
            exhausted=boundary is None,
        )
        return groups[:maximum_group] if maximum_group else groups

    @api.model
    def _get_selected_groupby_fields(self) -> list[str]:
        group_by_prefix = "group_by_"
        return [
            field_name.removeprefix(group_by_prefix)
            for field_name in self._fields
            if field_name.startswith(group_by_prefix) and self[field_name]
        ]

    @api.model
    def _get_selected_groupby(self) -> list[str]:
        groups = self._get_selected_groupby_fields()

        if not groups:
            raise UserError(
                self.env._(
                    "You have to specify a filter for your selection, or tick "
                    "Similar Names."
                )
            )

        if not self._IDENTIFYING_GROUPBY_FIELDS.intersection(groups):
            raise UserError(
                self.env._(
                    "Grouping on %(fields)s alone puts every contact sharing an "
                    "empty value in one group. Add Email, Name or VAT.",
                    fields=", ".join(sorted(groups)),
                )
            )

        return groups

    @api.model
    def _is_partner_used_in_models(
        self, aggr_ids: list[int], models: dict[str, str]
    ) -> bool:
        return any(
            self.env[model].search_count([(field, "in", aggr_ids)])
            for model, field in models.items()
        )

    @api.model
    def _get_ordered_partner(self, partner_ids: list[int]) -> models.BaseModel:
        return (
            self.env["res.partner"]
            .browse(partner_ids)
            .sorted(
                key=lambda p: (
                    not p.active,
                    (p.create_date or datetime.datetime(1970, 1, 1)),
                ),
                reverse=True,
            )
        )

    def _get_exclusion_models(self) -> dict[str, str]:
        model_mapping = {}
        if self.exclude_contact:
            model_mapping["res.users"] = "partner_id"
        if "account.move.line" in self.env and self.exclude_journal_item:
            model_mapping["account.move.line"] = "partner_id"
        return model_mapping

    def action_skip(self) -> dict[str, Any]:
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._action_next_screen()

    def _action_next_screen(self) -> dict[str, Any]:
        self.env.invalidate_all()
        values = {}
        if self.line_ids:
            current_line = self.line_ids[0]
            current_partner_ids = literal_eval(current_line.aggr_ids)
            values.update(
                {
                    "current_line_id": current_line.id,
                    "partner_ids": [Command.set(current_partner_ids)],
                    "dst_partner_id": self._get_ordered_partner(current_partner_ids)[
                        -1
                    ].id,
                    "state": "selection",
                }
            )
        else:
            values.update(
                {
                    "current_line_id": False,
                    "partner_ids": [],
                    "state": "finished",
                }
            )

        self.write(values)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _create_merge_lines_from_query(self, query: SQL) -> None:
        self.check_singleton()
        self.env.cr.execute(query)  # noqa: E8501  built via SQL() by _generate_query or action_process_parent_migration, not from user input
        self._create_merge_lines(self.env.cr.fetchall())

    def _create_merge_lines(self, groups: list[tuple[int, list[int]]]) -> None:
        self.check_singleton()
        model_mapping = self._get_exclusion_models()

        all_ids = [pid for _, aggr_ids in groups for pid in aggr_ids]
        accessible = self.env["res.partner"].search([("id", "in", all_ids)])
        accessible_set = set(accessible.ids)

        counter = 0
        for min_id, aggr_ids in groups:
            partner_ids = [pid for pid in aggr_ids if pid in accessible_set]
            if len(partner_ids) < 2:
                continue

            if model_mapping and self._is_partner_used_in_models(
                partner_ids, model_mapping
            ):
                continue

            self.env["base.partner.merge.line"].create(
                {
                    "wizard_id": self.id,
                    "min_id": min_id,
                    "aggr_ids": partner_ids,
                }
            )
            counter += 1

        self.write(
            {
                "state": "selection",
                "number_group": counter,
            }
        )

        _logger.info("counter: %s", counter)
        _debug.pipeline(
            "merge_lines",
            groups=len(groups),
            candidates=len(all_ids),
            accessible=len(accessible_set),
            lines=counter,
            exclusion_models=sorted(model_mapping),
        )

    def action_start_manual_process(self) -> dict[str, Any]:
        self.check_singleton()
        groups: list[tuple[int, list[int]]] = []

        if self._get_selected_groupby_fields() or not self.match_similar_names:
            exact_fields = self._get_selected_groupby()
            query = self._generate_query(exact_fields, self.maximum_group)
            self.env.cr.execute(query)  # noqa: E8501  built via SQL() by _generate_query
            groups.extend(self.env.cr.fetchall())
            _debug.pipeline("exact_groups", fields=exact_fields, groups=len(groups))

        if self.match_similar_names:
            groups.extend(self._get_similar_name_groups(self.maximum_group))

        self._create_merge_lines(groups)
        return self._action_next_screen()

    def action_start_automatic_process(self) -> dict[str, Any]:
        self.check_singleton()
        self.action_start_manual_process()
        self.env.invalidate_all()

        _debug.pipeline("automatic_merge", wizard=self.id, lines=len(self.line_ids))
        for line in self.line_ids:
            self._merge_duplicate_group(literal_eval(line.aggr_ids))
            line.unlink()
            self.env.cr.commit()

        self.write({"state": "finished"})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_process_parent_migration(self) -> dict[str, Any]:
        self.check_singleton()

        query = SQL("""
            SELECT
                min(p1.id),
                array_agg(DISTINCT p1.id)
            FROM
                res_partner as p1
            INNER join
                res_partner as p2
            ON
                p1.email = p2.email AND
                p1.name = p2.name AND
                (p1.parent_id = p2.id OR p1.id = p2.parent_id)
            WHERE
                p2.id IS NOT NULL
            GROUP BY
                p1.email,
                p1.name,
                CASE WHEN p1.parent_id = p2.id THEN p2.id
                    ELSE p1.id
                END
            HAVING COUNT(*) >= 2
            ORDER BY
                min(p1.id)
        """)

        self._create_merge_lines_from_query(query)

        _debug.pipeline("parent_migration", wizard=self.id, lines=len(self.line_ids))
        for line in self.line_ids:
            self._merge_duplicate_group(literal_eval(line.aggr_ids))
            line.unlink()
            self.env.cr.commit()

        self.write({"state": "finished"})

        self.env.cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL,
                parent_id = NULL
            WHERE
                parent_id = id
        """)
        _debug.lifecycle("self_parents_cleared", rows=self.env.cr.rowcount)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_update_all_process(self) -> dict[str, Any]:
        self.check_singleton()
        self.action_process_parent_migration()

        wizard = self.create(
            {
                "group_by_vat": True,
                "group_by_email": True,
                "group_by_name": True,
            }
        )
        wizard.action_start_automatic_process()

        self.env.cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL
            WHERE
                parent_id IS NOT NULL AND
                is_company IS NOT NULL
        """)

        return self._action_next_screen()

    def action_merge(self) -> dict[str, Any]:
        if len(self.partner_ids) > self._MERGE_SIZE_LIMIT:
            raise UserError(
                self.env._(
                    "For safety reasons, you cannot merge more than %(limit)s contacts "
                    "together. You can re-open the wizard several times if needed.",
                    limit=self._MERGE_SIZE_LIMIT,
                )
            )
        if not self.partner_ids:
            self.write({"state": "finished"})
            return {
                "type": "ir.actions.act_window",
                "res_model": self._name,
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
            }

        self._merge(self.partner_ids.ids, self.dst_partner_id)

        if self.current_line_id:
            self.current_line_id.unlink()

        return self._action_next_screen()
