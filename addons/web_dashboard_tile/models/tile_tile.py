# © 2010-2013 OpenERP s.a. (<http://openerp.com>).
# © 2014 initOS GmbH & Co. KG (<http://www.initos.com>).
# © 2015-Today GRAP
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging
import re

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

COLOR_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

FIELD_FUNCTIONS = {
    "count": {
        "name": "Count",
        "group_operator": None,
        "help": _("Number of records"),
    },
    "min": {
        "name": "Minimum",
        "group_operator": "min",
        "help": _("Minimum value of '%s'"),
    },
    "max": {
        "name": "Maximum",
        "group_operator": "max",
        "help": _("Maximum value of '%s'"),
    },
    "sum": {
        "name": "Sum",
        "group_operator": "sum",
        "help": _("Total value of '%s'"),
    },
    "avg": {
        "name": "Average",
        "group_operator": "avg",
        "help": _("Average value of '%s'"),
    },
    "median": {
        "name": "Median",
        "group_operator": None,
        "help": _("Median value of '%s'"),
    },
}

FIELD_FUNCTION_SELECTION = [
    (k, v["name"]) for k, v in FIELD_FUNCTIONS.items()
]


class TileTile(models.Model):
    _name = "tile.tile"
    _description = "Dashboard Tile"
    _order = "sequence, name"

    # --- Fields ---

    name = fields.Char(required=True)
    sequence = fields.Integer(default=0, required=True)
    category_id = fields.Many2one(
        string="Category",
        comodel_name="tile.category",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(string="User", comodel_name="res.users")
    background_color = fields.Char(default="#0E6C7E")
    font_color = fields.Char(default="#FFFFFF")
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Groups",
        help=(
            "If set, only users in these groups can view this tile. "
            "Only applies to global tiles (User field left empty)."
        ),
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(string="Model name", related="model_id.model")
    domain = fields.Text(default="[]", required=True)
    domain_error = fields.Char(compute="_compute_data", compute_sudo=True)
    action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Action",
        help="Leave empty to use the default action for the model.",
        domain="[('res_model', '=', model_name)]",
    )
    active = fields.Boolean(
        compute="_compute_active",
        search="_search_active",
        readonly=True,
    )
    hide_if_null = fields.Boolean(
        string="Hide if null",
        help="If checked, the tile is hidden when primary value is zero.",
    )
    hidden = fields.Boolean(
        compute="_compute_data",
        compute_sudo=True,
        search="_search_hidden",
    )

    # Primary Value
    primary_function = fields.Selection(
        required=True,
        selection=FIELD_FUNCTION_SELECTION,
        default="count",
    )
    primary_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Primary Field",
        domain=(
            "[('model_id', '=', model_id),"
            " ('ttype', 'in', ['float', 'integer', 'monetary'])]"
        ),
    )
    primary_format = fields.Char(
        help="Python format string, e.g. '{:,} Kgs' → '1,000 Kgs'.",
    )
    primary_value = fields.Float(compute="_compute_data", compute_sudo=True)
    primary_formated_value = fields.Char(compute="_compute_data", compute_sudo=True)
    primary_helper = fields.Char(compute="_compute_helper", store=True)
    primary_error = fields.Char(compute="_compute_data", compute_sudo=True)

    # Secondary Value
    secondary_function = fields.Selection(
        selection=FIELD_FUNCTION_SELECTION,
    )
    secondary_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Secondary Field",
        domain=(
            "[('model_id', '=', model_id),"
            " ('ttype', 'in', ['float', 'integer', 'monetary'])]"
        ),
    )
    secondary_format = fields.Char(
        help="Python format string, e.g. '{:,} Kgs' → '1,000 Kgs'.",
    )
    secondary_value = fields.Float(compute="_compute_data", compute_sudo=True)
    secondary_formated_value = fields.Char(compute="_compute_data", compute_sudo=True)
    secondary_helper = fields.Char(compute="_compute_helper", store=True)
    secondary_error = fields.Char(compute="_compute_data", compute_sudo=True)

    # --- Constraints ---

    @api.constrains("model_id", "primary_field_id", "secondary_field_id")
    def _check_model_id_field_id(self):
        for tile in self:
            for field_rec in (tile.primary_field_id, tile.secondary_field_id):
                if field_rec and field_rec.model_id != tile.model_id:
                    raise ValidationError(
                        _("Please select a field from the selected model."),
                    )

    @api.constrains("background_color", "font_color")
    def _check_color_format(self):
        """Prevent CSS injection via color fields."""
        for tile in self:
            for field_name in ("background_color", "font_color"):
                value = tile[field_name]
                if value and not COLOR_HEX_RE.match(value):
                    raise ValidationError(
                        _(
                            "Color must be a valid hex code "
                            "(e.g. #0E6C7E), got: %(color)s",
                            color=value,
                        ),
                    )

    # --- Compute: tile data ---

    @api.depends(
        "model_id",
        "domain",
        "primary_format",
        "primary_function",
        "primary_field_id",
        "secondary_format",
        "secondary_function",
        "secondary_field_id",
    )
    def _compute_data(self):
        for tile in self:
            tile._reset_computed_values()
            if not tile.model_id or not tile.active:
                continue
            try:
                tile._compute_tile_values()
            except Exception:
                _logger.warning(
                    "Error computing tile '%s' (id=%s)",
                    tile.name,
                    tile.id,
                    exc_info=True,
                )

    def _reset_computed_values(self):
        """Set all computed fields to safe defaults."""
        self.hidden = False
        self.primary_value = 0.0
        self.primary_formated_value = False
        self.secondary_value = 0.0
        self.secondary_formated_value = False
        self.domain_error = False
        self.primary_error = False
        self.secondary_error = False

    def _compute_tile_values(self):
        """Compute primary/secondary values for one tile."""
        self.ensure_one()
        model = self.env[self.model_id.model]
        eval_ctx = self._get_eval_context()
        try:
            parsed_domain = safe_eval(self.domain or "[]", eval_ctx)
        except (ValueError, SyntaxError, TypeError) as exc:
            self.domain_error = str(exc)
            self.primary_formated_value = _("Domain Error")
            self.secondary_formated_value = _("Domain Error")
            return

        try:
            count = model.search_count(parsed_domain)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.domain_error = str(exc)
            self.primary_formated_value = _("Domain Error")
            self.secondary_formated_value = _("Domain Error")
            return

        for prefix in ("primary_", "secondary_"):
            self._compute_single_value(prefix, model, parsed_domain, count)
        self.hidden = self.hide_if_null and not self.primary_value

    def _compute_single_value(self, prefix, model, domain, count):
        """Compute one aggregated value (primary or secondary)."""
        self.ensure_one()
        func_key = self[prefix + "function"]
        field_rec = self[prefix + "field_id"]
        fmt = self[prefix + "format"]

        if not func_key:
            return
        if func_key == "count":
            value = count
        elif not field_rec:
            return
        else:
            value = self._aggregate_field(
                model, domain, field_rec.name, func_key,
            )

        self[prefix + "value"] = value
        try:
            self[prefix + "formated_value"] = (fmt or "{:,}").format(value)
        except (ValueError, KeyError, IndexError) as exc:
            self[prefix + "formated_value"] = _("Format Error")
            self[prefix + "error"] = str(exc)

    def _aggregate_field(self, model, domain, field_name, func_key):
        """Use SQL aggregation (read_group) when possible.

        Falls back to search_read + Python for non-stored fields,
        and an efficient offset-based median.
        """
        if func_key == "median":
            return self._compute_median(model, domain, field_name)

        group_op = FIELD_FUNCTIONS.get(func_key, {}).get("group_operator")
        if group_op:
            try:
                spec = f"{field_name}:{group_op}"
                result = model.read_group(domain, [spec], [], lazy=False)
                return (
                    (result[0].get(field_name, 0.0) or 0.0) if result else 0.0
                )
            except (ValueError, NotImplementedError):
                # Non-stored / computed field — fallback to Python
                return self._aggregate_python(
                    model, domain, field_name, func_key,
                )
        return 0.0

    def _aggregate_python(self, model, domain, field_name, func_key):
        """Fallback aggregation via search_read for non-stored fields."""
        records = model.search_read(domain, [field_name])
        values = [
            r[field_name]
            for r in records
            if isinstance(r[field_name], (int, float))
        ]
        if not values:
            return 0.0
        if func_key == "sum":
            return sum(values)
        if func_key == "avg":
            return sum(values) / len(values)
        if func_key == "min":
            return min(values)
        if func_key == "max":
            return max(values)
        return 0.0

    @staticmethod
    def _compute_median(model, domain, field_name):
        """Memory-efficient median: fetches at most 2 records."""
        count = model.search_count(domain)
        if not count:
            return 0.0
        order = f"{field_name} ASC"
        mid = count // 2
        if count % 2 == 1:
            recs = model.search_read(
                domain, [field_name], limit=1, offset=mid, order=order,
            )
            return recs[0][field_name] if recs else 0.0
        recs = model.search_read(
            domain, [field_name], limit=2, offset=mid - 1, order=order,
        )
        if len(recs) == 2:
            return (recs[0][field_name] + recs[1][field_name]) / 2
        return recs[0][field_name] if recs else 0.0

    # --- Compute: helpers ---

    @api.depends(
        "primary_function",
        "primary_field_id",
        "secondary_function",
        "secondary_field_id",
    )
    def _compute_helper(self):
        for tile in self:
            for prefix in ("primary_", "secondary_"):
                func_key = tile[prefix + "function"]
                field_rec = tile[prefix + "field_id"]
                info = FIELD_FUNCTIONS.get(func_key, {})
                help_text = info.get("help", "")
                if help_text and func_key != "count" and field_rec:
                    tile[prefix + "helper"] = (
                        help_text % field_rec.field_description
                    )
                else:
                    tile[prefix + "helper"] = help_text or ""

    def _compute_active(self):
        IrModelAccess = self.env["ir.model.access"]
        for tile in self:
            tile.active = (
                IrModelAccess.check(tile.model_id.model, "read", False)
                if tile.model_id
                else True
            )

    # --- Search ---

    def _search_hidden(self, operator, operand):
        """Optimized: only evaluate tiles that CAN be hidden.

        Uses active_test=False to avoid recursive implicit active filter.
        """
        candidates = self.with_context(active_test=False).search(
            [("hide_if_null", "=", True)],
        )
        hidden_ids = [t.id for t in candidates if t.hidden]
        if (operator == "=" and operand is False) or (
            operator == "!=" and operand is True
        ):
            return [("id", "not in", hidden_ids)]
        return [("id", "in", hidden_ids)]

    def _search_active(self, operator, value):
        if operator != "=":
            raise UserError(
                _("Unsupported search operator on Active field."),
            )
        IrModelAccess = self.env["ir.model.access"]
        self.env.cr.execute(
            "SELECT tt.id, im.model "
            "FROM tile_tile tt "
            "JOIN ir_model im ON tt.model_id = im.id",
        )
        ids = [
            row[0]
            for row in self.env.cr.fetchall()
            if IrModelAccess.check(row[1], "read", False) == value
        ]
        return [("id", "in", ids)]

    # --- Onchange ---

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.primary_field_id = False
        self.secondary_field_id = False
        self.action_id = False

    @api.onchange("primary_function", "secondary_function")
    def _onchange_function(self):
        if self.primary_function in (False, "count"):
            self.primary_field_id = False
        if self.secondary_function in (False, "count"):
            self.secondary_field_id = False

    # --- Actions ---

    def open_link(self):
        """Return an action to open the tile's filtered model view."""
        self.ensure_one()
        eval_ctx = self._get_eval_context()
        try:
            parsed_domain = safe_eval(self.domain or "[]", eval_ctx)
        except (ValueError, SyntaxError, TypeError):
            parsed_domain = []

        if self.action_id:
            action = self.action_id.read()[0]
        else:
            action = {
                "view_mode": "list",
                "view_id": False,
                "res_model": self.model_id.model,
                "type": "ir.actions.act_window",
                "target": "current",
            }
        action.update(
            {
                "name": self.name,
                "display_name": self.name,
                "context": dict(self.env.context, group_by=False),
                "domain": parsed_domain,
            },
        )
        return action

    # --- Helpers ---

    @api.model
    def _get_eval_context(self):
        """Minimal eval context for safe_eval — no env.context leak."""
        return {
            "uid": self.env.uid,
            "user": self.env.user,
            "relativedelta": relativedelta,
            "context_today": fields.Date.from_string(
                fields.Date.context_today(self),
            ),
            "current_date": fields.Date.today(),
        }
