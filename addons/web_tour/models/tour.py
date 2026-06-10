from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError
import json


class Web_TourTour(models.Model):
    _name = 'web_tour.tour'
    _description = "Tour"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    step_ids = fields.One2many("web_tour.tour.step", "tour_id")
    url = fields.Char(string="Starting URL", default="/odoo")
    sharing_url = fields.Char(compute="_compute_sharing_url", string="Sharing URL")
    rainbow_man_message = fields.Html(default="<b>Good job!</b> You went through all steps of this tour.", translate=True)
    sequence = fields.Integer(default=1000)
    custom = fields.Boolean(string="Custom")
    user_consumed_ids = fields.Many2many("res.users")

    _uniq_name = models.Constraint(
        'unique(name)',
        "A tour already exists with this name . Tour's name must be unique!",
    )

    @api.depends("name")
    def _compute_sharing_url(self):
        for tour in self:
            tour.sharing_url = f"{tour.get_base_url()}/odoo?tour={tour.name}"

    @api.model
    def consume(self, tourName):
        if self.env.user and self.env.user._is_internal():
            tour_id = self.search([("name", "=", tourName)])
            if tour_id:
                tour_id.sudo().user_consumed_ids = [Command.link(self.env.user.id)]
        return self.get_current_tour()

    @api.model
    def get_current_tour(self):
        if self.env.user and self.env.user.tour_enabled and self.env.user._is_internal():
            tours_to_run = self.search([("custom", "=", False), ("user_consumed_ids", "not in", self.env.user.id)])
            return bool(tours_to_run[:1]) and tours_to_run[:1]._get_tour_json()

    @api.model
    def get_tour_json_by_name(self, tour_name):
        tour_id = self.search([("name", "=", tour_name)])
        if not tour_id:
            return False
        return tour_id._get_tour_json()

    def _get_tour_json(self):
        tour_json = self.read(fields={
            "name",
            "url",
            "custom"
        })[0]

        del tour_json["id"]
        tour_json["steps"] = self.step_ids.get_steps_json()
        tour_json["rainbowManMessage"] = self.rainbow_man_message
        return tour_json

    def export_js_file(self):
        js_content = f"""import {{ registry }} from '@web/core/registry';

registry.category("web_tour.tours").add("{self.name}", {{
    url: "{self.url}",
    steps: () => {json.dumps(self.step_ids.get_steps_json(), indent=4)}
}})"""

        attachment_id = self.env["ir.attachment"].create({
            "raw": bytes(js_content, 'utf-8'),
            "name": f"{self.name}.js",
            "mimetype": "application/javascript",
            "res_model": "web_tour.tour",
            "res_id": self.id,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}?download=true",
        }


class Web_TourTourStep(models.Model):
    _name = 'web_tour.tour.step'
    _description = "Tour's step"
    _order = "sequence, id"

    trigger = fields.Char(required=True)
    content = fields.Html(translate=True)
    tooltip_position = fields.Selection(selection=[
        ["bottom", "Bottom"],
        ["top", "Top"],
        ["right", "Right"],
        ["left", "left"],
    ], default="bottom")
    is_active = fields.Json()
    tour_id = fields.Many2one("web_tour.tour", required=True, index=True, ondelete="cascade")
    run = fields.Char()
    sequence = fields.Integer()

    _VALID_ACTIVE_TAGS = {"community", "enterprise", "mobile", "desktop"}

    @api.constrains("is_active")
    def _check_is_active(self):
        for step in self:
            value = step.is_active
            if not value:
                continue
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    raise ValidationError("is_active must be a valid JSON array.")
            if not isinstance(value, list):
                raise ValidationError("is_active must be a JSON array.")
            if not all(isinstance(v, str) for v in value):
                raise ValidationError("is_active values must be strings.")
            invalid = {v for v in value
                       if v not in self._VALID_ACTIVE_TAGS
                       and not set(".#[:>~+(").intersection(v)}
            if invalid:
                raise ValidationError(
                    f"Invalid is_active value(s): {invalid}. "
                    f"Allowed keywords: {self._VALID_ACTIVE_TAGS}"
                )

    def get_steps_json(self):
        steps = []

        for step in self.read(fields=["trigger", "content", "run", "tooltip_position", "is_active"]):
            del step["id"]
            if step["tooltip_position"]:
                step["tooltipPosition"] = step["tooltip_position"]
            del step["tooltip_position"]

            if not step["content"]:
                del step["content"]
            if step["is_active"]:
                step["isActive"] = step["is_active"]
            del step["is_active"]
            steps.append(step)

        return steps
