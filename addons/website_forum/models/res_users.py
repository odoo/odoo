from odoo import _, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    create_date = fields.Datetime(
        string="Create Date",
        index=True,
        readonly=True,
    )

    def open_website_url(self):
        return self.mapped("partner_id").open_website_url()

    def get_gamification_redirection_data(self):
        res = super().get_gamification_redirection_data()
        res.append(
            {
                "label": _("See our Forum"),
                "url": "/forum",
            }
        )
        return res
