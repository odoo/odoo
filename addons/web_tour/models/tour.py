from odoo import api, fields, models, Command
import json
import base64


class Tour(models.Model):
    _name = "web_tour.tour"
    _description = "Tours"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    step_ids = fields.One2many("web_tour.tour.step", "tour_id")
    url = fields.Char(string="Starting URL", default="/odoo")
    sharing_url = fields.Char(compute="_compute_sharing_url", string="Sharing URL")
    rainbow_man_message = fields.Html(default="<b>Good job!</b> You went through all steps of this tour.", translate=True)
    sequence = fields.Integer(default=1000)
    custom = fields.Boolean(string="Custom")
    user_consumed_ids = fields.Many2many("res.users")

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "A tour already exists with this name . Tour's name must be unique!"),
    ]

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
            "datas": base64.b64encode(bytes(js_content, 'utf-8')),
            "name": f"{self.name}.js",
            "mimetype": "application/javascript",
            "res_model": "web_tour.tour",
            "res_id": self.id,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}?download=true",
        }


class TourStep(models.Model):
    _name = "web_tour.tour.step"
    _description = "Tour's step"
    _order = "sequence, id"

    trigger = fields.Char(required=True)
    content = fields.Char()
    tour_id = fields.Many2one("web_tour.tour", required=True, ondelete="cascade")
    run = fields.Char()
    sequence = fields.Integer()

    def get_steps_json(self):
        steps = []

        for step in self.read(fields=["trigger", "content", "run"]):
            del step["id"]
            if not step["content"]:
                del step["content"]
            steps.append(step)

        return steps
