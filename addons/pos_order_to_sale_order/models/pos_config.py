# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    iface_create_sale_order = fields.Boolean(
        string="Create Sale Orders",
        compute="_compute_iface_create_sale_order",
        store=True,
    )

    iface_create_draft_sale_order = fields.Boolean(
        string="Create Draft Sale Orders",
        default=True,
        help="If checked, the cashier will have the possibility to create"
        " a draft Sale Order, based on the current draft PoS Order.",
    )

    iface_create_confirmed_sale_order = fields.Boolean(
        string="Create Confirmed Sale Orders",
        default=True,
        help="If checked, the cashier will have the possibility to create"
        " a confirmed Sale Order, based on the current draft PoS Order.",
    )

    iface_create_delivered_sale_order = fields.Boolean(
        string="Create Delivered Sale Orders",
        default=True,
        help="If checked, the cashier will have the possibility to create"
        " a confirmed sale Order, based on the current draft PoS Order.\n"
        " the according picking will be marked as delivered. Only invoices"
        " process will be possible.",
    )

    iface_create_invoiced_sale_order = fields.Boolean(
        string="Create Invoiced Sale Orders",
        default=True,
        help="If checked, the cashier will have the possibility to create"
        " a confirmed sale Order, based on the current draft PoS Order.\n"
        " the according picking will be marked as delivered.\n"
        " The Invoice will be generated and confirm.\n"
        " Only invoice payment process will be possible.",
    )

    @api.depends(
        "iface_create_draft_sale_order",
        "iface_create_confirmed_sale_order",
        "iface_create_delivered_sale_order",
        "iface_create_invoiced_sale_order",
    )
    def _compute_iface_create_sale_order(self):
        for config in self:
            config.iface_create_sale_order = any(
                [
                    config.iface_create_draft_sale_order,
                    config.iface_create_confirmed_sale_order,
                    config.iface_create_delivered_sale_order,
                    config.iface_create_invoiced_sale_order,
                ]
            )
