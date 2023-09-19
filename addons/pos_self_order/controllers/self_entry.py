# -*- coding: utf-8 -*-
import werkzeug

from odoo import http
from odoo.http import request


class PosSelfKiosk(http.Controller):
    @http.route(["/pos-self/<config_id>", "/pos-self/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def start_self_ordering(self, config_id=None, access_token=None, table_identifier=None):
        table_sudo = False

        if not config_id or not config_id.isnumeric():
            raise werkzeug.exceptions.NotFound()

        if access_token:
            config_access_token = True
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ('access_token', '=', access_token)], limit=1)
        else:
            config_access_token = False
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id)], limit=1)

        if not pos_config_sudo or pos_config_sudo.self_ordering_mode == 'nothing':
            raise werkzeug.exceptions.NotFound()

        company = pos_config_sudo.company_id
        user = pos_config_sudo.current_session_id.user_id or pos_config_sudo.self_ordering_default_user_id
        pos_config = pos_config_sudo.sudo(False).with_company(company).with_user(user)

        if not pos_config:
            raise werkzeug.exceptions.NotFound()

        if pos_config and pos_config.has_active_session and pos_config.self_ordering_mode == 'mobile':
            if config_access_token:
                config_access_token = pos_config.access_token
            table_sudo = table_identifier and (
                request.env["restaurant.table"]
                .sudo()
                .search([("identifier", "=", table_identifier), ("active", "=", True)], limit=1)
            )
        elif pos_config.self_ordering_mode == 'kiosk':
            if config_access_token:
                config_access_token = pos_config.access_token

        table = table_sudo.sudo(False).with_company(company).with_user(user) if table_sudo else False

        return request.render(
                'pos_self_order.index',
                {
                    'session_info': {
                        **request.env["ir.http"].get_frontend_session_info(),
                        'currencies': request.env["ir.http"].get_currencies(),
                        'pos_self_order_data': {
                            'table': table._get_self_order_data() if table else False,
                            'access_token': config_access_token,
                            **pos_config._get_self_ordering_data(),
                        },
                        "base_url": request.env['pos.session'].get_base_url(),
                    }
                }
            )

    @http.route(
        "/pos-self/get-category-image/<int:category_id>",
        methods=["GET"],
        type="http",
        auth="public",
    )
    def pos_self_order_get_cat_image(self, category_id: int):
        category = request.env["pos.category"].sudo().browse(category_id)

        if not category.has_image:
            raise werkzeug.exceptions.NotFound()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(
                category,
                field_name="image_128",
            )
            .get_response()
        )

    @http.route(
        [
            "/menu/get-image/<int:product_id>",
            "/menu/get-image/<int:product_id>/<int:image_size>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def pos_self_order_get_image(self, product_id, image_size=128, **kw):
        # This controller is public and does not require an access code (access_token) because the user
        # needs to see the product image in "menu" mode. In this mode, the user has no access_token.
        self.get_any_pos_config_sudo()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(
                request.env["product.product"].sudo().browse(product_id),
                field_name=f"image_{image_size}",
            )
            .get_response()
        )

    def get_any_pos_config_sudo(self):
        pos_config_sudo = request.env["pos.config"].sudo().search([
            ("self_ordering_mode", "not in", ['nothing'])], limit=1)

        if not pos_config_sudo:
            raise werkzeug.exceptions.NotFound()

        return pos_config_sudo
