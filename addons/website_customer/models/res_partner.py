from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    website_tag_ids = fields.Many2many(
        comodel_name="res.partner.website.tag",
        relation="res_partner_res_partner_website_tag_rel",
        column1="partner_id",
        column2="tag_id",
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
    def _selection_classname(self):
        classname = ["info", "primary", "success", "warning", "danger"]
        return [(x, str.title(x)) for x in classname]

    name = fields.Char(
        string="Tag Name",
        translate=True,
        required=True,
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="res_partner_res_partner_website_tag_rel",
        column1="tag_id",
        column2="partner_id",
        string="Partners",
    )
    classname = fields.Selection(
        selection="_selection_classname",
        string="Class",
        default="info",
        required=True,
        help="Bootstrap class to customize the color",
    )
    active = fields.Boolean(default=True)

    def _default_is_published(self):
        return True
