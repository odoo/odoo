import typing
from collections import defaultdict
from collections.abc import Collection
from typing import Literal, NamedTuple, Self

from odoo import Command, api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput
from odoo.addons.mail.tools.recipients import (
    RecipientData,
    RecipientRow,
    prepare_recipient_data,
)

if typing.TYPE_CHECKING:
    from .mail_message_subtype import MailMessageSubtype
    from .res_partner import ResPartner


_debug = DebugLog(__name__)

ExistingPolicy = Literal["skip", "replace", "update"]


class SubscriptionRow(NamedTuple):
    id: int
    res_model: str
    res_id: int
    partner_id: int
    subtype_ids: list[int]
    partner_share: bool
    partner_active: bool


_RECIPIENT_USER_LATERAL = """
 LEFT JOIN LATERAL (
        SELECT users.id AS uid,
               users.share AS share,
               users.notification_type AS notification_type,
               ARRAY_AGG(groups_rel.gid) FILTER (WHERE groups_rel.gid IS NOT NULL) AS groups
          FROM res_users users
     LEFT JOIN res_groups_users_rel groups_rel ON groups_rel.uid = users.id
         WHERE users.partner_id = partner.id AND users.active
      GROUP BY users.id
      ORDER BY users.share ASC NULLS LAST, users.id ASC
         FETCH FIRST ROW ONLY
         ) sub_user ON TRUE"""

_RECIPIENT_PARTNER_COLUMNS = """
           partner.id AS pid,
           partner.active AS active,
           partner.email_normalized AS email_normalized,
           partner.lang AS lang,
           partner.name AS name,
           partner.partner_share AS pshare,
           sub_user.uid AS uid,
           COALESCE(sub_user.share, FALSE) AS ushare,
           COALESCE(sub_user.notification_type, 'email') AS notif,
           sub_user.groups AS groups"""

_RECIPIENT_FOLLOWERS_QUERY = f"""
    WITH sub_followers AS (
        SELECT fol.partner_id AS pid,
               fol.res_id AS res_id,
               TRUE AS is_follower,
               subrel.mail_followers_id IS NOT NULL AS subtype_follower,
               subrel.mail_followers_id IS NOT NULL
               AND COALESCE(
                       (SELECT subtype.internal
                          FROM mail_message_subtype subtype
                         WHERE subtype.id = %(subtype_id)s),
                       FALSE
                   ) AS internal
          FROM mail_followers fol
     LEFT JOIN mail_followers_mail_message_subtype_rel subrel
            ON subrel.mail_followers_id = fol.id
           AND subrel.mail_message_subtype_id = %(subtype_id)s
         WHERE fol.res_model = %(res_model)s
           AND fol.res_id = ANY(%(res_ids)s)
           AND (subrel.mail_followers_id IS NOT NULL
                OR fol.partner_id = ANY(%(pids)s))

         UNION ALL

        SELECT res_partner.id AS pid,
               0 AS res_id,
               FALSE AS is_follower,
               FALSE AS subtype_follower,
               FALSE AS internal
          FROM res_partner
         WHERE res_partner.id = ANY(%(pids)s)
    )
    SELECT {_RECIPIENT_PARTNER_COLUMNS},
           sub_followers.res_id AS res_id,
           sub_followers.is_follower AS is_follower
      FROM res_partner partner
      JOIN sub_followers ON sub_followers.pid = partner.id
{_RECIPIENT_USER_LATERAL}
     WHERE (sub_followers.subtype_follower
            AND (sub_followers.internal IS NOT TRUE OR partner.partner_share IS NOT TRUE))
        OR partner.id = ANY(%(pids)s)
"""

_RECIPIENT_PARTNERS_QUERY = f"""
    SELECT {_RECIPIENT_PARTNER_COLUMNS},
           ARRAY_AGG(fol.res_id) FILTER (WHERE fol.res_id IS NOT NULL) AS res_ids
      FROM res_partner partner
 LEFT JOIN mail_followers fol ON fol.partner_id = partner.id
                             AND fol.res_model = %(res_model)s
                             AND fol.res_id = ANY(%(res_ids)s)
{_RECIPIENT_USER_LATERAL}
     WHERE partner.id = ANY(%(pids)s)
  GROUP BY partner.id,
           sub_user.uid,
           sub_user.share,
           sub_user.notification_type,
           sub_user.groups
"""

_SUBSCRIPTION_DATA_QUERY = """
    SELECT fol.id,
           fol.res_model,
           fol.res_id,
           fol.partner_id,
           COALESCE(
               ARRAY_AGG(subtype.id ORDER BY subtype.id)
               FILTER (WHERE subtype.id IS NOT NULL), '{}'),
           partner.partner_share,
           partner.active
      FROM mail_followers fol
 LEFT JOIN mail_followers_mail_message_subtype_rel fol_rel
        ON fol_rel.mail_followers_id = fol.id
 LEFT JOIN mail_message_subtype subtype ON subtype.id = fol_rel.mail_message_subtype_id
 LEFT JOIN res_partner partner ON partner.id = fol.partner_id
     WHERE %(where)s
  GROUP BY fol.id, partner.partner_share, partner.active
"""

_RECIPIENT_READS = {
    "mail.followers": ("partner_id", "res_id", "res_model", "subtype_ids"),
    "mail.message.subtype": ("internal",),
    "res.groups": ("user_ids",),
    "res.partner": ("active", "email_normalized", "lang", "name", "partner_share"),
    "res.users": ("active", "group_ids", "notification_type", "partner_id", "share"),
}

_SUBSCRIPTION_READS = {
    "mail.followers": ("partner_id", "res_id", "res_model", "subtype_ids"),
    "res.partner": ("active", "partner_share"),
}

_FOLLOWER_WRITES = {
    "mail.followers": ("partner_id", "res_id", "res_model", "subtype_ids"),
}

_MAIL_DOC_READS = {
    "mail.followers": ("partner_id", "res_id", "res_model"),
    "mail.mail": ("mail_message_id", "recipient_ids"),
    "mail.message": ("model", "res_id"),
}


class MailFollowers(models.Model):
    _name = "mail.followers"
    _log_access = False
    _description = "Document Followers"

    res_model = fields.Char(
        string="Related Document Model Name",
        required=True,
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Related Document ID",
        index=True,
        help="Id of the followed resource",
    )
    partner_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        string="Related Partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    subtype_ids: MailMessageSubtype = fields.Many2many(
        comodel_name="mail.message.subtype",
        help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall.",
    )
    is_active = fields.Boolean(
        related="partner_id.active",
        string="Is Active",
    )

    _mail_followers_res_partner_res_model_id_uniq = models.Constraint(
        "unique nulls not distinct (res_model,res_id,partner_id)",
        "Error, a partner cannot follow twice the same object.",
    )

    _FOLLOWED_FNAMES = ("message_follower_ids",)

    def _fields_read_by(self, reads: dict[str, tuple[str, ...]]) -> list[fields.Field]:
        return [
            self.env[model]._fields[fname]
            for model, fnames in reads.items()
            for fname in fnames
        ]

    def _invalidate_documents(
        self, documents: list[tuple[str, int]] | None = None
    ) -> None:
        to_invalidate = defaultdict(list)
        for res_model, res_id in (
            documents
            if documents is not None
            else [(record.res_model, record.res_id) for record in self]
        ):
            if res_id:
                to_invalidate[res_model].append(res_id)
        for res_model, res_ids in to_invalidate.items():
            if res_model not in self.env:
                continue
            records = self.env[res_model].browse(res_ids)
            fnames = [
                fname for fname in self._FOLLOWED_FNAMES if fname in records._fields
            ]
            if fnames:
                records.invalidate_recordset(fnames)
                records.modified(fnames)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(res),
            models=sorted({vals.get("res_model") or "" for vals in vals_list}),
        )
        res._invalidate_documents()
        return res

    def write(self, vals: ValuesType) -> Literal[True]:
        moved = {"res_model", "res_id"} & vals.keys()
        _debug.lifecycle(
            "write", followers=self.ids, fields=list(vals), moved=bool(moved)
        )
        if moved:
            self._invalidate_documents()
        res = super().write(vals)
        if moved or "partner_id" in vals:
            self._invalidate_documents()
        return res

    def unlink(self) -> Literal[True]:
        documents = [(record.res_model, record.res_id) for record in self]
        _debug.lifecycle("unlink", followers=self.ids, documents=len(set(documents)))
        res = super().unlink()
        self._invalidate_documents(documents)
        return res

    @api.depends("partner_id.display_name")
    def _compute_display_name(self) -> None:
        for follower in self:
            follower.display_name = follower.partner_id.sudo().display_name

    @api.model
    def _get_mail_doc_to_followers(
        self, mail_ids: list[int]
    ) -> dict[tuple[str, int], set[int]]:
        if not mail_ids:
            return {}
        rows = self.env.execute_query(
            SQL(
                """
            SELECT message.model, message.res_id, mail_partner.res_partner_id
              FROM mail_mail mail
              JOIN mail_mail_res_partner_rel mail_partner ON mail_partner.mail_mail_id = mail.id
              JOIN mail_message message ON mail.mail_message_id = message.id
              JOIN mail_followers follower ON message.model = follower.res_model
               AND message.res_id = follower.res_id
               AND mail_partner.res_partner_id = follower.partner_id
             WHERE mail.id = ANY(%(mail_ids)s)
        """,
                mail_ids=list(mail_ids),
                to_flush=self._fields_read_by(_MAIL_DOC_READS),
            )
        )
        res = defaultdict(set)
        for model, doc_id, partner_id in rows:
            res[(model, doc_id)].add(partner_id)
        return dict(res)

    def _get_recipient_data(
        self,
        records: models.BaseModel | None,
        message_type: str,
        subtype_id: int,
        pids: Collection[int] = (),
        *,
        include_followers: bool = True,
    ) -> dict[int, dict[int, RecipientData]]:
        pids = list(pids or ())
        res_ids = records.ids if records else [0]
        params = {
            "subtype_id": subtype_id or 0,
            "res_model": records._get_reference_model_name() if records else "",
            "res_ids": records.ids if records else [],
            "pids": pids,
        }
        to_flush = self._fields_read_by(_RECIPIENT_READS)
        if (
            include_followers
            and message_type != "user_notification"
            and records
            and subtype_id
        ):
            res = [
                RecipientRow._make(row)
                for row in self.env.execute_query(
                    SQL(_RECIPIENT_FOLLOWERS_QUERY, to_flush=to_flush, **params)
                )
            ]
        elif pids:
            res = []
            for row in self.env.execute_query(
                SQL(_RECIPIENT_PARTNERS_QUERY, to_flush=to_flush, **params)
            ):
                followed = frozenset(row[-1] or ())
                res += [
                    RecipientRow._make((*row[:-1], res_id, res_id in followed))
                    for res_id in res_ids
                ]
        else:
            res = []
        _debug.perf.count(
            "recipient_rows_fetched",
            model=records._name if records else None,
            records=len(res_ids),
            message_type=message_type,
            subtype=subtype_id or None,
            partners=len(pids),
            include_followers=include_followers,
            rows=len(res),
        )

        doc_infos: dict[int, dict[int, RecipientData]] = {
            res_id: {} for res_id in res_ids
        }
        group_definitions = None
        group_closure_cache: dict[frozenset[int], frozenset[int]] = {
            frozenset(): frozenset()
        }
        for row in res:
            to_update = [row.res_id] if row.res_id else res_ids
            group_key = frozenset(row.group_ids or ())
            group_ids = group_closure_cache.get(group_key)
            if group_ids is None:
                if group_definitions is None:
                    group_definitions = self.env["res.groups"]._get_group_definitions()
                group_ids = group_key | frozenset(
                    group_definitions.get_superset_ids(group_key)
                )
                group_closure_cache[group_key] = group_ids
            for res_id_to_update in to_update:
                if not row.res_id and row.partner_id in doc_infos[res_id_to_update]:
                    continue
                doc_infos[res_id_to_update][row.partner_id] = prepare_recipient_data(
                    partner_id=row.partner_id,
                    active=row.active,
                    email_normalized=row.email_normalized,
                    groups=group_ids,
                    is_follower=row.is_follower,
                    lang=row.lang,
                    name=row.name,
                    notif=row.notif,
                    partner_share=row.partner_share,
                    uid=row.uid,
                    user_share=row.user_share,
                )

        return doc_infos

    def _get_subscription_data(
        self,
        doc_data: list[tuple[str, list[int]]],
        partner_ids: Collection[int] | None,
    ) -> list[SubscriptionRow]:
        if not doc_data:
            return []
        if partner_ids is not None and not partner_ids:
            return []
        where = SQL(" OR ").join(
            SQL("fol.res_model = %s AND fol.res_id = ANY(%s)", res_model, list(res_ids))
            for res_model, res_ids in doc_data
        )
        if partner_ids is not None:
            where = SQL("(%s) AND fol.partner_id = ANY(%s)", where, list(partner_ids))
        rows = self.env.execute_query(
            SQL(
                _SUBSCRIPTION_DATA_QUERY,
                where=where,
                to_flush=self._fields_read_by(_SUBSCRIPTION_READS),
            )
        )
        _debug.perf.count(
            "subscription_rows_fetched",
            models=len(doc_data),
            partners=None if partner_ids is None else len(partner_ids),
            rows=len(rows),
        )
        return [SubscriptionRow._make(row) for row in rows]

    def _add_followers(
        self,
        res_model: str,
        res_ids: Collection[int],
        partner_ids: Collection[int],
        customer_ids: Collection[int] | None = None,
        check_existing: bool = True,
        existing_policy: ExistingPolicy = "skip",
    ) -> None:
        if not res_ids or not partner_ids:
            return
        subtypes = self._get_get_subtypes(res_model, partner_ids, customer_ids)
        self._add_followers_multi(
            res_model,
            dict.fromkeys(res_ids, subtypes),
            check_existing=check_existing,
            existing_policy=existing_policy,
        )

    def _add_followers_multi(
        self,
        res_model: str,
        subtypes_per_record: dict[int, dict[int, list[int]]],
        check_existing: bool = True,
        existing_policy: ExistingPolicy = "skip",
    ) -> None:
        new_vals, updates = self._prepare_followers_vals(
            res_model,
            subtypes_per_record,
            check_existing=check_existing,
            existing_policy=existing_policy,
        )
        sudo_self = self.sudo()
        _debug.pipeline(
            "add_followers",
            model=res_model,
            records=len(subtypes_per_record),
            new=len(new_vals),
            updates=len(updates),
            check_existing=check_existing,
            policy=existing_policy,
        )
        if new_vals:
            raced = self._create_followers(sudo_self, new_vals)
            if raced and existing_policy != "skip":
                _debug.logic(
                    "followers_raced",
                    model=res_model,
                    raced=len(raced),
                    policy=existing_policy,
                )
                raced_per_record = defaultdict(dict)
                for res_id, partner_id in raced:
                    raced_per_record[res_id][partner_id] = subtypes_per_record[res_id][
                        partner_id
                    ]
                _new, raced_updates = self._prepare_followers_vals(
                    res_model,
                    dict(raced_per_record),
                    check_existing=True,
                    existing_policy=existing_policy,
                )
                updates.update(raced_updates)
        by_payload = defaultdict(list)
        for fol_id, (add_sids, remove_sids) in updates.items():
            by_payload[(add_sids, remove_sids)].append(fol_id)
        for (add_sids, remove_sids), fol_ids in by_payload.items():
            sudo_self.browse(fol_ids).write(
                {
                    "subtype_ids": [Command.link(sid) for sid in sorted(add_sids)]
                    + [Command.unlink(sid) for sid in sorted(remove_sids)]
                }
            )

    def _create_followers(
        self, sudo_self: Self, new_vals: list[ValuesType]
    ) -> list[tuple[int, int]]:
        subtype_ids_by_key: dict[tuple[int, int], list[int]] = {}
        res_models, res_ids, partner_ids = [], [], []
        for vals in new_vals:
            res_models.append(vals["res_model"])
            res_ids.append(vals["res_id"])
            partner_ids.append(vals["partner_id"])
            subtype_ids_by_key[(vals["res_id"], vals["partner_id"])] = [
                sid for command in vals.get("subtype_ids") or () for sid in command[2]
            ]
        rows = self.env.execute_query(
            SQL(
                """
            INSERT INTO mail_followers (res_model, res_id, partner_id)
                 SELECT * FROM unnest(%(res_models)s::varchar[],
                                      %(res_ids)s::int[],
                                      %(partner_ids)s::int[])
            ON CONFLICT DO NOTHING
              RETURNING id, res_id, partner_id
        """,
                res_models=res_models,
                res_ids=res_ids,
                partner_ids=partner_ids,
                to_flush=self._fields_read_by(_FOLLOWER_WRITES),
            )
        )
        created = {(res_id, partner_id): fol_id for fol_id, res_id, partner_id in rows}
        subtype_rows = [
            (fol_id, subtype_id)
            for key, fol_id in created.items()
            for subtype_id in subtype_ids_by_key[key]
        ]
        if subtype_rows:
            self.env.execute_query(
                SQL(
                    """
                INSERT INTO mail_followers_mail_message_subtype_rel
                            (mail_followers_id, mail_message_subtype_id)
                     SELECT * FROM unnest(%(fol_ids)s::int[], %(subtype_ids)s::int[])
                ON CONFLICT DO NOTHING
            """,
                    fol_ids=[row[0] for row in subtype_rows],
                    subtype_ids=[row[1] for row in subtype_rows],
                )
            )
        self.env["mail.followers"].invalidate_model()
        self._invalidate_documents(list(zip(res_models, res_ids, strict=True)))
        _debug.lifecycle(
            "followers_created",
            asked=len(new_vals),
            created=len(created),
            subtype_rows=len(subtype_rows),
        )
        return [key for key in subtype_ids_by_key if key not in created]

    def _get_get_subtypes(
        self,
        res_model: str,
        partner_ids: Collection[int],
        customer_ids: Collection[int] | None = None,
    ) -> dict[int, list[int]]:
        if not partner_ids:
            return {}

        default, _, external = self.env["mail.message.subtype"].default_subtypes(
            res_model
        )
        if customer_ids is None:
            customer_ids = (
                self.env["res.partner"]
                .sudo()
                .with_context(active_test=False)
                .search(
                    [("id", "in", partner_ids), ("partner_share", "=", True)],
                    order="id",
                )
                .ids
            )
        customer_ids = set(customer_ids)

        return {
            pid: external.ids if pid in customer_ids else default.ids
            for pid in partner_ids
        }

    def _prepare_followers_vals(
        self,
        res_model: str,
        subtypes_per_record: dict[int, dict[int, Collection[int]]],
        check_existing: bool = True,
        existing_policy: ExistingPolicy = "skip",
    ) -> tuple[list[ValuesType], dict[int, tuple[frozenset, frozenset]]]:
        res_ids = list(subtypes_per_record)
        partner_ids = {
            pid for subtypes in subtypes_per_record.values() for pid in subtypes
        }
        existing = {}

        if check_existing and res_ids and partner_ids:
            existing = {
                (row.res_id, row.partner_id): (row.id, row.subtype_ids)
                for row in self._get_subscription_data(
                    [(res_model, res_ids)], partner_ids
                )
            }

        new_vals, updates = [], {}
        for res_id, subtypes in subtypes_per_record.items():
            for partner_id, subtype_ids in subtypes.items():
                if (found := existing.get((res_id, partner_id))) is None:
                    new_vals.append(
                        {
                            "res_model": res_model,
                            "res_id": res_id,
                            "partner_id": partner_id,
                            "subtype_ids": [Command.set(sorted(subtype_ids))],
                        }
                    )
                elif existing_policy in ("replace", "update"):
                    fol_id, current_sids = found
                    add_sids = frozenset(subtype_ids) - frozenset(current_sids)
                    remove_sids = (
                        frozenset(current_sids) - frozenset(subtype_ids)
                        if existing_policy == "replace"
                        else frozenset()
                    )
                    if add_sids or remove_sids:
                        updates[fol_id] = (add_sids, remove_sids)

        return new_vals, updates

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            "display_name",
            "is_active",
            Store.One("partner_id", sudo=True),
            Store.One("thread", [], as_thread=True),
        ]
