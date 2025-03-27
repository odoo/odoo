# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_iface_create_draft_sale_order = fields.Boolean(
        related="pos_config_id.iface_create_draft_sale_order", readonly=False
    )

    pos_iface_create_confirmed_sale_order = fields.Boolean(
        related="pos_config_id.iface_create_confirmed_sale_order", readonly=False
    )

    pos_iface_create_delivered_sale_order = fields.Boolean(
        related="pos_config_id.iface_create_delivered_sale_order", readonly=False
    )

    pos_iface_create_invoiced_sale_order = fields.Boolean(
        related="pos_config_id.iface_create_invoiced_sale_order", readonly=False
    )
