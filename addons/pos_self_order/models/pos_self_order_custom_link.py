from markupsafe import escape

from odoo import api, fields, models


class Pos_Self_OrderCustom_Link(models.Model):
    _name = "pos_self_order.custom_link"
    _inherit = ["mixin.pos.load"]
    _description = "Custom links that the restaurant can configure to be displayed on the self order screen"
    name = fields.Char(
        string="Label",
        translate=True,
        required=True,
    )
    url = fields.Char(
        string="URL",
        required=True,
    )
    pos_config_ids = fields.Many2many(
        comodel_name="pos.config",
        string="Points of Sale",
        domain="[('self_ordering_mode', '!=', 'nothing')]",
        help="Select for which points of sale you want to display this link. Leave empty to display it for all points of sale. You have to select among the points of sale that have the 'QR Code Menu' feature enabled.",
    )
    style = fields.Selection(
        selection=[
            ("primary", "Primary"),
            ("secondary", "Secondary"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("danger", "Danger"),
            ("info", "Info"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        default="primary",
        required=True,
    )
    link_html = fields.Html(
        string="Preview",
        compute="_compute_link_html",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=1)

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [("pos_config_ids", "in", config.id)]

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ["name", "url", "style", "link_html", "sequence"]

    @api.depends("name", "style")
    def _compute_link_html(self):
        for link in self:
            if link.name:
                link.link_html = (
                    f'<a class="btn btn-{link.style} w-100">{escape(link.name)}</a>'
                )
