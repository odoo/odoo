from odoo import _, api, exceptions, fields, models
from odoo.db import get_or_create_row

from ._canvas import SCALE_MAX, SCALE_MIN


class AutomationCanvasViewport(models.Model):
    _name = "automation.canvas.viewport"
    _description = "Workflow Canvas Viewport"
    _rec_name = "automation_rule_id"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Reader",
        default=lambda self: self.env.user,
        index=True,
        required=True,
        ondelete="cascade",
    )
    automation_rule_id = fields.Many2one(
        comodel_name="automation.rule",
        index=True,
        required=True,
        ondelete="cascade",
    )
    pos_x = fields.Float(
        string="Canvas X",
        help="Horizontal translation of the canvas, in screen pixels",
    )
    pos_y = fields.Float(
        string="Canvas Y",
        help="Vertical translation of the canvas, in screen pixels",
    )
    scale = fields.Float(
        default=1.0,
        help="Zoom factor of the canvas, 1.0 being unzoomed",
    )

    _viewport_uniq = models.Constraint(
        "UNIQUE(user_id, automation_rule_id)",
        "A reader keeps one canvas viewport per automation.",
    )

    @api.constrains("scale")
    def _check_scale(self):
        for viewport in self:
            if not SCALE_MIN <= viewport.scale <= SCALE_MAX:
                raise exceptions.ValidationError(
                    _(
                        "A canvas zoom of %(scale)s is outside the "
                        "%(minimum)s-%(maximum)s the canvas can draw.",
                        scale=viewport.scale,
                        minimum=SCALE_MIN,
                        maximum=SCALE_MAX,
                    )
                )

    @api.model
    def _search_own(self, automation_rule):
        return self.search(
            [
                ("user_id", "=", self.env.uid),
                ("automation_rule_id", "=", automation_rule.id),
            ],
            limit=1,
        )

    @api.model
    def _get_viewport(self, automation_rule):
        viewport = self._search_own(automation_rule)
        if not viewport:
            return None
        return {
            "x": viewport.pos_x,
            "y": viewport.pos_y,
            "scale": viewport.scale,
        }

    @api.model
    def _update_viewport(self, automation_rule, x, y, scale):
        """Store the caller's viewport, racing safely against their own tabs.

        Two tabs reach this with no row in either, and `_viewport_uniq` refuses
        the second INSERT. `get_or_create_row` is the framework's own recovery:
        insert inside a *flushing* savepoint and take the winner's row. A bare
        savepoint leaves the ORM cache describing a row the rollback removed.
        """
        vals = {"pos_x": x, "pos_y": y, "scale": scale}
        viewport = self._search_own(automation_rule)
        if viewport:
            viewport.write(vals)
            return viewport
        viewport, created = get_or_create_row(
            self.env.cr,
            lambda: self.create(
                {
                    **vals,
                    "user_id": self.env.uid,
                    "automation_rule_id": automation_rule.id,
                }
            ),
            lambda: self._search_own(automation_rule),
            conflict=f"A canvas viewport for automation {automation_rule.id}",
        )
        if not created:
            viewport.write(vals)
        return viewport
