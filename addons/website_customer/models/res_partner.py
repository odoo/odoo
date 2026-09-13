from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    website_tag_ids = fields.Many2many(
        "res.partner.website.tag",
        "res_partner_res_partner_website_tag_rel",
        "partner_id",
        "tag_id",
        string="Website tags",
        help="Filter published customers on the .../customers website page",
    )

    def get_backend_menu_id(self):
        return self.env.ref("partner.partner_menu_root").id


class ResPartnerWebsiteTag(models.Model):
    _name = "res.partner.website.tag"

    _description = "Website Tag (published label for the customer references page)"
    _inherit = ["mixin.website.published"]

    @api.model
    def get_selection_class(self):
        classname = ["info", "primary", "success", "warning", "danger"]
        return [(x, str.title(x)) for x in classname]

    name = fields.Char("Tag Name", required=True, translate=True)
    partner_ids = fields.Many2many(
        "res.partner",
        "res_partner_res_partner_website_tag_rel",
        "tag_id",
        "partner_id",
        string="Partners",
    )
    classname = fields.Selection(
        "get_selection_class",
        "Class",
        default="info",
        help="Bootstrap class to customize the color",
        required=True,
    )
    active = fields.Boolean(default=True)

    def _default_is_published(self):
        return True
