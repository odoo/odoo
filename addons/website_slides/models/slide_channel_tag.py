from odoo import api, fields, models


class SlideChannelTagGroup(models.Model):
    _name = "slide.channel.tag.group"
    _description = "Channel/Course Groups"
    _inherit = ["mixin.website.published"]
    _order = "sequence asc"

    name = fields.Char(
        string="Group Name",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        default=10,
        index=True,
        required=True,
    )
    tag_ids = fields.One2many(
        comodel_name="slide.channel.tag",
        inverse_name="group_id",
        string="Tags",
    )

    def _default_is_published(self):
        return True


class SlideChannelTag(models.Model):
    _name = "slide.channel.tag"
    _inherit = ["mixin.color"]
    _description = "Channel/Course Tag"
    _order = "group_sequence asc, sequence asc"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        default=10,
        index=True,
        required=True,
    )
    group_id = fields.Many2one(
        comodel_name="slide.channel.tag.group",
        index=True,
        required=True,
        ondelete="cascade",
    )
    group_sequence = fields.Integer(
        related="group_id.sequence",
        string="Group sequence",
        readonly=True,
    )
    channel_ids = fields.Many2many(
        comodel_name="slide.channel",
        relation="slide_channel_tag_rel",
        column1="tag_id",
        column2="channel_id",
        string="Channels",
    )
    color = fields.Integer(
        string="Color Index",
        default=lambda self: self._default_color(),
        help="Tag color used in both backend and website. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags",
    )

    @api.model
    def _search_by_slugs(self, slugs):
        try:
            tag_ids = [
                tag_id
                for tag_id in (
                    self.env["ir.http"]._unslug(slug)[1]
                    for slug in (slugs or "").split(",")
                )
                if tag_id
            ]
        except Exception:
            return self.browse()
        return self.search([("id", "in", tag_ids)]) if tag_ids else self.browse()
