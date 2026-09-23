from typing import Any, Literal

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import ormcache

_debug = DebugLog(__name__)


class IrModel(models.Model):
    _inherit = "ir.model"
    _order = "is_mail_thread DESC, name ASC"

    is_mail_thread = fields.Boolean(
        string="Has Mail Thread",
        default=False,
    )
    is_mail_activity = fields.Boolean(
        string="Has Mail Activity",
        default=False,
    )
    is_mail_blacklist = fields.Boolean(
        string="Has Mail Blacklist",
        default=False,
    )

    @api.model
    @ormcache()
    def _get_mail_blacklist_models(self) -> tuple[str, ...]:
        blacklist_models = self.sudo().search(
            [
                ("is_mail_blacklist", "=", True),
                ("model", "!=", "mixin.mail.thread.blacklist"),
            ]
        )
        _debug.perf.count("blacklist_models_computed", models=len(blacklist_models))
        return tuple(
            model.model for model in blacklist_models if model.model in self.env
        )

    def unlink(self) -> Literal[True]:
        if not self:
            return True

        mail_models = self.search(
            [
                (
                    "model",
                    "in",
                    (
                        "mail.activity",
                        "mail.activity.type",
                        "mail.followers",
                        "mail.message",
                    ),
                )
            ],
            order="id",
        )

        if not (self & mail_models):
            models = list(self.mapped("model"))
            model_ids = list(self.ids)

            query = "DELETE FROM mail_activity WHERE res_model_id = ANY(%s)"
            self.env.cr.execute(query, [model_ids])

            query = "DELETE FROM mail_activity_type WHERE res_model = ANY(%s)"
            self.env.cr.execute(query, [models])

            query = "DELETE FROM mail_followers WHERE res_model = ANY(%s)"
            self.env.cr.execute(query, [models])

            query = "DELETE FROM mail_message WHERE model = ANY(%s)"
            self.env.cr.execute(query, [models])

        models = list(self.mapped("model"))
        query = """
            SELECT DISTINCT store_fname
            FROM ir_attachment
            WHERE res_model = ANY(%s) AND store_fname IS NOT NULL
            EXCEPT
            SELECT store_fname
            FROM ir_attachment
            WHERE res_model != ALL(%s);
        """
        self.env.cr.execute(query, [models, models])
        fnames = [fname for (fname,) in self.env.cr.fetchall()]

        query = """DELETE FROM ir_attachment WHERE res_model = ANY(%s)"""
        self.env.cr.execute(query, [models])

        _debug.lifecycle(
            "mail_data_purged",
            models=models,
            purged_mail_tables=not (self & mail_models),
            orphan_files=len(fnames),
        )
        if fnames:
            self.env["ir.attachment"]._remove_stored_file_multi(fnames)

        return super().unlink()

    def write(self, vals: ValuesType) -> Literal[True]:
        if self and (
            "is_mail_thread" in vals
            or "is_mail_activity" in vals
            or "is_mail_blacklist" in vals
        ):
            if any(rec.state != "manual" for rec in self):
                raise UserError(self.env._("Only custom models can be modified."))
            if "is_mail_thread" in vals and any(
                rec.is_mail_thread > vals["is_mail_thread"] for rec in self
            ):
                raise UserError(
                    self.env._('Field "Mail Thread" cannot be changed to "False".')
                )
            if "is_mail_activity" in vals and any(
                rec.is_mail_activity > vals["is_mail_activity"] for rec in self
            ):
                raise UserError(
                    self.env._('Field "Mail Activity" cannot be changed to "False".')
                )
            if "is_mail_blacklist" in vals and any(
                rec.is_mail_blacklist > vals["is_mail_blacklist"] for rec in self
            ):
                raise UserError(
                    self.env._('Field "Mail Blacklist" cannot be changed to "False".')
                )
            res = super().write(vals)
            self.env.flush_all()
            model_names = self.mapped("model")
            self.pool.setup_models(self.env.cr, model_names)
            model_names = self.pool.get_descendants(model_names, "_inherits")
            with _debug.perf(
                "mail_flags_init_models",
                cr=self.env.cr,
                models=model_names,
                flags=sorted(
                    k
                    for k in ("is_mail_thread", "is_mail_activity", "is_mail_blacklist")
                    if k in vals
                ),
            ):
                self.pool.init_models(
                    self.env.cr,
                    model_names,
                    dict(self.env.context, update_custom_fields=True),
                )
        else:
            res = super().write(vals)
        return res

    def _prepare_model_vals(self, model: models.BaseModel) -> dict[str, Any]:
        vals = super()._prepare_model_vals(model)
        vals["is_mail_thread"] = isinstance(model, self.pool["mixin.mail.thread"])
        vals["is_mail_activity"] = isinstance(model, self.pool["mixin.mail.activity"])
        vals["is_mail_blacklist"] = isinstance(
            model, self.pool["mixin.mail.thread.blacklist"]
        )
        return vals

    @api.model
    def _prepare_class_attrs(self, model_data: dict) -> dict:
        attrs = super()._prepare_class_attrs(model_data)
        if (
            model_data.get("is_mail_blacklist")
            and attrs["_name"] != "mixin.mail.thread.blacklist"
        ):
            parents = attrs.get("_inherit") or []
            parents = [parents] if isinstance(parents, str) else parents
            attrs["_inherit"] = parents + ["mixin.mail.thread.blacklist"]
            if attrs["_custom"]:
                attrs["_primary_email"] = "x_email"
        elif model_data.get("is_mail_thread") and attrs["_name"] != "mixin.mail.thread":
            parents = attrs.get("_inherit") or []
            parents = [parents] if isinstance(parents, str) else parents
            attrs["_inherit"] = parents + ["mixin.mail.thread"]
        if (
            model_data.get("is_mail_activity")
            and attrs["_name"] != "mixin.mail.activity"
        ):
            parents = attrs.get("_inherit") or []
            parents = [parents] if isinstance(parents, str) else parents
            attrs["_inherit"] = parents + ["mixin.mail.activity"]
        return attrs

    def _get_definitions(self, model_names: list[str]) -> dict:
        return self._mail_annotate_definitions(super()._get_definitions(model_names))

    def _get_model_definitions(self, model_names_to_fetch: list[str]) -> dict:
        return self._mail_annotate_definitions(
            super()._get_model_definitions(model_names_to_fetch)
        )

    def _mail_annotate_definitions(self, model_definitions: dict) -> dict:
        for model_name, model_definition in model_definitions.items():
            model = self.env[model_name]
            if isinstance(model, self.env.registry["mixin.mail.thread"]):
                fields = model_definition["fields"]
                for fname in model._track_get_fields():
                    if fname in fields:
                        fields[fname]["tracking"] = True
            if isinstance(model, self.env.registry["mixin.mail.activity"]):
                model_definition["has_activities"] = True
        return model_definitions
