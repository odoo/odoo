import json

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import file_open

_debug = DebugLog(__name__)


class SpreadsheetDashboard(models.Model):
    _name = "spreadsheet.dashboard"
    _description = "Spreadsheet Dashboard"
    _inherit = ["mixin.spreadsheet", "mixin.user.favorite"]
    _order = "sequence"

    name = fields.Char(
        translate=True,
        required=True,
    )
    dashboard_group_id = fields.Many2one(
        comodel_name="spreadsheet.dashboard.group",
        index=True,
        required=True,
    )
    sequence = fields.Integer()
    sample_dashboard_file_path = fields.Char(export_string_translation=False)
    is_published = fields.Boolean(default=True)
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        default=lambda self: self.env.ref("base.group_user"),
    )
    favorite_user_ids = fields.Many2many(
        string="Favorite Users",
        domain=lambda self: [("id", "=", self.env.uid)],
        help="Users who have favorited this dashboard",
    )
    is_user_favorite = fields.Boolean(
        string="Is Favorite",
        help="Indicates whether the dashboard is favorited by the current user",
    )
    main_data_model_ids = fields.Many2many(
        comodel_name="ir.model",
        copy=False,
    )

    def _get_serialized_readonly_dashboard(self):
        snapshot = json.loads(self.spreadsheet_data)
        user_locale = self.env["res.lang"]._get_user_spreadsheet_locale()
        snapshot.setdefault("settings", {})["locale"] = user_locale
        default_currency = self.env[
            "res.currency"
        ].get_company_currency_for_spreadsheet()
        return json.dumps(
            {
                "snapshot": snapshot,
                "revisions": [],
                "default_currency": default_currency,
                "translation_namespace": self._get_dashboard_translation_namespace(),
            }
        )

    def _get_sample_dashboard(self):
        try:
            with file_open(self.sample_dashboard_file_path) as f:
                return json.load(f)
        except FileNotFoundError:
            _debug.logic(
                "dashboard_sample_file_missing",
                dashboard=self,
                path=self.sample_dashboard_file_path,
            )
            return None

    def _dashboard_is_empty(self):
        empty_model = next(
            (
                model
                for model in self.sudo().main_data_model_ids.mapped("model")
                if self.env[model].search_count([], limit=1) == 0
            ),
            None,
        )
        _debug.logic(
            "dashboard_emptiness_checked", dashboard=self, first_empty_model=empty_model
        )
        return empty_model is not None

    def _get_dashboard_translation_namespace(self):
        data = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=", self._name),
                    ("res_id", "in", self.ids),
                ],
                limit=1,
            )
        )
        return data.module

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for dashboard, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", dashboard.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        # ``copy_data`` renames ``name`` in the duplicating user's language
        # only; without this the copy would keep the source record's exact
        # ``name`` in every other language.
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )
