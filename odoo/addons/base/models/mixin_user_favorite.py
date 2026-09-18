from typing import Any

from odoo import Command, api, fields, models
from odoo.fields import Domain, Field
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class MixinUserFavorite(models.AbstractModel):
    _name = "mixin.user.favorite"
    _description = "User Favorite Mixin"

    favorite_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Favorite of",
        export_string_translation=False,
        copy=False,
    )
    is_user_favorite = fields.Boolean(
        string="Favorite",
        export_string_translation=False,
        compute="_compute_is_user_favorite",
        inverse="_inverse_is_user_favorite",
        search="_search_is_user_favorite",
        compute_sudo=True,
        order_by_sql="_is_user_favorite_order_sql",
    )

    @api.depends("favorite_user_ids")
    @api.depends_context("uid")
    def _compute_is_user_favorite(self) -> None:
        uid = self.env.uid
        favorited = 0  # debuglog
        for record in self:
            record.is_user_favorite = uid in record.favorite_user_ids.ids
            favorited += record.is_user_favorite  # debuglog
        _debug.perf.count(
            "user_favorite_computed",
            model=self._name,
            uid=uid,
            records=len(self),
            favorited=favorited,
        )

    def _inverse_is_user_favorite(self) -> None:
        favorited = self.filtered("is_user_favorite")
        _debug.pipeline(
            "user_favorite_inverse",
            model=self._name,
            records=len(self),
            favorited=len(favorited),
        )
        favorited._update_user_favorite(True)
        (self - favorited)._update_user_favorite(False)

    def _update_user_favorite(self, is_favorite: bool) -> None:
        if not self:
            _debug.logic(
                "user_favorite_skipped", model=self._name, reason="empty_recordset"
            )
            return
        self._check_user_favorite_access()
        command = Command.link if is_favorite else Command.unlink
        _debug.lifecycle(
            "user_favorite",
            model=self._name,
            records=self.ids,
            uid=self.env.uid,
            favorite=is_favorite,
        )
        self.sudo().favorite_user_ids = [command(self.env.uid)]

    def _check_user_favorite_access(self) -> None:
        self.check_access("read")

    @api.model
    def _search_is_user_favorite(self, operator: str, value: Any) -> Domain:
        if operator != "in":
            _debug.logic(
                "user_favorite_search_unsupported",
                model=self._name,
                operator=operator,
            )
            return NotImplemented
        favorited = Domain("favorite_user_ids", "in", [self.env.uid])
        _debug.logic(
            "user_favorite_search",
            model=self._name,
            uid=self.env.uid,
            value=list(value),
        )
        if set(value) == {True}:
            return favorited
        if set(value) == {False}:
            return ~favorited
        return NotImplemented

    def action_toggle_user_favorite(self) -> None:
        favorited = self.filtered("is_user_favorite")
        _debug.lifecycle(
            "user_favorite_toggled",
            model=self._name,
            records=len(self),
            unfavorited=len(favorited),
            favorited=len(self) - len(favorited),
        )
        favorited._update_user_favorite(False)
        (self - favorited)._update_user_favorite(True)

    @api.model_create_multi
    def create(self, vals_list):
        wanted = [bool(vals.get("is_user_favorite")) for vals in vals_list]
        records = super().create(
            [
                {k: v for k, v in vals.items() if k != "is_user_favorite"}
                for vals in vals_list
            ]
        )
        favorited = records.browse(
            [
                record.id
                for record, is_favorite in zip(records, wanted, strict=True)
                if is_favorite
            ]
        )
        _debug.lifecycle(
            "create", model=self._name, count=len(records), favorited=len(favorited)
        )
        favorited._update_user_favorite(True)
        return records

    def write(self, vals):
        if "is_user_favorite" in vals:
            vals = dict(vals)
            self._update_user_favorite(vals.pop("is_user_favorite"))
            if not vals:
                _debug.logic("write_favorite_only", model=self._name, count=len(self))
                return True
        return super().write(vals)

    def _is_user_favorite_order_sql(
        self, field: Field, alias: str, direction: SQL, nulls: SQL, query: Any
    ) -> SQL:
        favorites = self._fields["favorite_user_ids"]
        sql_field = SQL(
            "%s IN (SELECT %s FROM %s WHERE %s = %s)",
            SQL.identifier(alias, "id"),
            SQL.identifier(favorites.column1),
            SQL.identifier(favorites.relation),
            SQL.identifier(favorites.column2),
            self.env.uid,
        )
        _debug.logic(
            "user_favorite_order_sql",
            model=self._name,
            uid=self.env.uid,
            any_value=bool(query._any_value_orderby),
            groupby=bool(query._collect_order_groupby),
        )
        return self._order_value_to_sql(sql_field, direction, nulls, query)
