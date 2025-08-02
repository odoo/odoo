# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api
from markupsafe import escape


class PosSelfOrderCustomLink(models.Model):
    _name = "pos_self_order.custom_link"
    _description = (
        "Custom links that the restaurant can configure to be displayed on the self order screen"
    )
    name = fields.Char(string="Label", required=True, translate=True)
    url = fields.Char(string="URL", required=True)
    pos_config_ids = fields.Many2many(
        "pos.config",
        string="Points of Sale",
        domain="[('self_ordering_mode', '!=', 'nothing')]",
        help="Select for which points of sale you want to display this link. Leave empty to display it for all points of sale. You have to select among the points of sale that have the 'QR Code Menu' feature enabled.",
    )
    style = fields.Selection(
        [
            ("primary", "Primary"),
            ("secondary", "Secondary"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("danger", "Danger"),
            ("info", "Info"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        string="Style",
        default="primary",
        required=True,
    )
    link_html = fields.Html("Preview", compute="_compute_link_html", store=True, readonly=True)
    sequence = fields.Integer("Sequence", default=1)

    @api.depends("name", "style")
    def _compute_link_html(self):
        for link in self:
            if link.name:
                link.link_html = f'<a class="btn btn-{link.style} w-100">{escape(link.name)}</a>'
