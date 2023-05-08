# -*- coding: utf-8 -*-

from werkzeug.urls import url_quote

from odoo import models, fields, api
from odoo.tools import split_every


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_view_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_table_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_pay_after = fields.Selection(
        [("each", "Each Order"), ("meal", "Meal")],
        string="Pay After:",
        default="each",
        help="Choose when the customer will pay",
        store=True,
        readonly=False,
        required=True,
    )
    pos_self_order_image = fields.Image(
        compute="_compute_pos_module_pos_self_order",
        store=True,
        readonly=False,
        max_width=1920,
        max_height=1080,
    )
    pos_self_order_image_name = fields.Char(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )

    @api.depends("pos_config_id")
    def _compute_pos_module_pos_self_order(self):
        for res_config in self:
            if not res_config.pos_config_id.self_order_view_mode:
                res_config.update(
                    {
                        "pos_self_order_view_mode": False,
                        "pos_self_order_table_mode": False,
                        "pos_self_order_pay_after": "each",
                        "pos_self_order_image": False,
                        "pos_self_order_image_name": False,
                    }
                )
            else:
                res_config.update(
                    {
                        "pos_self_order_view_mode": res_config.pos_config_id.self_order_view_mode,
                        "pos_self_order_table_mode": res_config.pos_config_id.self_order_table_mode,
                        "pos_self_order_pay_after": res_config.pos_config_id.self_order_pay_after,
                        "pos_self_order_image": res_config.pos_config_id.self_order_image,
                        "pos_self_order_image_name": res_config.pos_config_id.self_order_image_name,
                    }
                )

    # self_order_table_mode is only available if self_order_view_mode is True
    @api.onchange("pos_self_order_view_mode")
    def _onchange_pos_self_order_view_mode(self):
        if not self.pos_self_order_view_mode:
            self.pos_self_order_table_mode = False

    @api.onchange("pos_self_order_table_mode")
    def _onchange_pos_self_order_table_mode(self):
        if self.pos_self_order_table_mode:
            self.pos_self_order_view_mode = True

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        no_OF_QR_CODES_PER_PAGE = 9
        no_OF_QR_CODES_PER_LINE = 3

        if self.pos_config_id.self_order_table_mode:
            tables_sudo = self.env["restaurant.table"].search(
                [("floor_id.pos_config_ids", "=", self.pos_config_id.id), ("active", "=", True)]
            )
            qr_codes_to_print = [
                {
                    "id": table.id,
                    "name": table.name,
                    "url": url_quote(
                        self.get_base_url() + self.pos_config_id._get_self_order_route(table.id)
                    ),
                }
                for table in tables_sudo
            ]
        else:
            qr_codes_to_print = [
                {
                    "id": 0,
                    "url": url_quote(self.get_base_url() + self.pos_config_id._get_self_order_route()),
                }
                for i in range(no_OF_QR_CODES_PER_PAGE)
            ]
        rows_of_tables = list(split_every(no_OF_QR_CODES_PER_LINE, qr_codes_to_print, list))
        pages_of_tables = list(
            split_every(no_OF_QR_CODES_PER_PAGE // no_OF_QR_CODES_PER_LINE, rows_of_tables, list)
        )
        # TODO: we might also want to group the tables by floor
        data = {
            "pages_of_tables": pages_of_tables,
        }
        return self.env.ref("pos_self_order.report_self_order_qr_codes_page").report_action(
            [], data=data
        )

    def preview_self_order_app(self):
        self.ensure_one()
        return self.pos_config_id.preview_self_order_app()
