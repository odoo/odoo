from odoo import fields, models


class EventBoothRegistration(models.Model):
    _inherit = "event.booth.registration"

    sponsor_name = fields.Char()
    sponsor_email = fields.Char()
    sponsor_phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_booth_registration_sponsor_phone_number_rel",
        column1="registration_id",
        column2="phone_number_id",
    )
    sponsor_subtitle = fields.Char(string="Sponsor Slogan")
    sponsor_website_description = fields.Html(
        string="Sponsor Description",
        sanitize_overridable=True,
    )
    sponsor_image_512 = fields.Image(string="Sponsor Logo")

    def _get_fields_for_booth_confirmation(self):
        return super()._get_fields_for_booth_confirmation() + [
            "sponsor_name",
            "sponsor_email",
            "sponsor_phone_ids",
            "sponsor_subtitle",
            "sponsor_website_description",
            "sponsor_image_512",
        ]
