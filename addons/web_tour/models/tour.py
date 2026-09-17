import re

from lxml import etree

from odoo import api, fields, models, Command


class Web_TourTour(models.Model):
    _name = 'web_tour.tour'
    _description = "Tour"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
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
        return tour_id._get_tour_json() if tour_id else False

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

    def export_xml_file(self):
        self.ensure_one()
        tour_xmlid = re.sub(r"\W", "_", self.name, flags=re.ASCII)

        odoo_el = etree.Element("odoo")
        tour_record = etree.SubElement(odoo_el, "record", {"id": tour_xmlid, "model": "web_tour.tour"})
        etree.SubElement(tour_record, "field", {"name": "name"}).text = self.name
        etree.SubElement(tour_record, "field", {"name": "sequence"}).text = str(self.sequence)
        etree.SubElement(tour_record, "field", {"name": "custom", "eval": str(self.custom)})
        etree.SubElement(tour_record, "field", {"name": "active", "eval": str(self.active)})
        if self.url:
            etree.SubElement(tour_record, "field", {"name": "url"}).text = self.url
        if self.rainbow_man_message:
            etree.SubElement(tour_record, "field", {"name": "rainbow_man_message"}).text = self.rainbow_man_message

        for index, step in enumerate(self.step_ids, start=1):
            step_record = etree.SubElement(odoo_el, "record", {
                "id": f"{tour_xmlid}_step_{index}",
                "model": "web_tour.tour.step",
            })
            etree.SubElement(step_record, "field", {"name": "tour_id", "ref": tour_xmlid})
            etree.SubElement(step_record, "field", {"name": "sequence"}).text = str(index * 10)
            etree.SubElement(step_record, "field", {"name": "trigger"}).text = step.trigger
            if step.run:
                etree.SubElement(step_record, "field", {"name": "run"}).text = step.run
            if step.content:
                etree.SubElement(step_record, "field", {"name": "content"}).text = step.content
            if step.tooltip_position:
                etree.SubElement(step_record, "field", {"name": "tooltip_position"}).text = step.tooltip_position

        etree.indent(odoo_el, space="    ")
        xml_content = etree.tostring(odoo_el, pretty_print=True, xml_declaration=True, encoding="utf-8")

        attachment_id = self.env["ir.attachment"].create({
            "raw": xml_content,
            "name": f"{self.name}.xml",
            "mimetype": "application/xml",
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
    content = fields.Char()
    tooltip_position = fields.Selection(selection=[
        ["bottom", "Bottom"],
        ["top", "Top"],
        ["right", "Right"],
        ["left", "left"],
    ], default="bottom")
    tour_id = fields.Many2one("web_tour.tour", required=True, index=True, ondelete="cascade")
    run = fields.Char()
    sequence = fields.Integer()

    def get_steps_json(self):
        steps = []

        for step in self.read(fields=["trigger", "content", "run", "tooltip_position"]):
            del step["id"]
            step["tooltipPosition"] = step["tooltip_position"]
            del step["tooltip_position"]

            if not step["content"]:
                del step["content"]
            if not step["run"]:
                del step["run"]
            steps.append(step)

        return steps
