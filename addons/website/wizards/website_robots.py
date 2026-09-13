from odoo import fields, models


class WebsiteRobots(models.TransientModel):
    _name = "website.robots"
    _description = "Robots.txt Editor"

    website_id = fields.Many2one(
        comodel_name="website",
        default=lambda s: s.env["website"].get_current_website(),
    )
    content = fields.Text(
        default=lambda s: s.env["website"].get_current_website().robots_txt
    )

    def action_save(self):
        website = self.website_id or self.env["website"].get_current_website()
        website.robots_txt = self.content
        return {"type": "ir.actions.act_window_close"}
