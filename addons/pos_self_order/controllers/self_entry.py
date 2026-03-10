import werkzeug

from odoo import http
from odoo.http import request


class PosSelfKiosk(http.Controller):
    @http.route(['/pos-self-order/<self_order_config_id>', '/pos-self-order/<self_order_config_id>/<path:subpath>'], auth='public', website=True, csrf=False)
    def start_new_self_ordering(self, self_order_config_id, access_token=None):
        self_order_config_id, access_token = self._verify_entry_access(self_order_config_id, access_token)
        return request.render(
            'pos_self_order.index',
            {
                'access_token': access_token,
                'session_info': {
                    **request.env["ir.http"].get_frontend_session_info(),
                    'currencies': request.env["res.currency"].get_all_currencies(),
                    'data': {
                        'config_id': self_order_config_id.id,
                        'self_ordering_mode': self_order_config_id.ordering_mode,
                    },
                    "base_url": request.env['pos.session'].get_base_url(),
                    "db": request.env.cr.dbname,
                },
            },
        )

    @http.route("/pos-self-order/data/<self_order_config_id>", type='jsonrpc', auth='public', website=True, readonly=True)
    def get_self_ordering_data(self, self_order_config_id, access_token=None):
        pos_config, access_token = self._verify_entry_access(self_order_config_id, access_token)
        data = pos_config.load_self_data()
        data['pos.self.order.config'][0]['access_token'] = access_token
        return data

    @http.route("/pos-self-order/receipt-template/<self_order_config_id>", type='jsonrpc', auth='public', readonly=True)
    def get_self_ordering_receipt_template(self, self_order_config_id):
        pos_config, _ = self._verify_entry_access(self_order_config_id)
        return pos_config.env['pos.order'].get_receipt_template_for_pos_frontend()

    @http.route("/pos-self-order/relations/<self_order_config_id>", type='jsonrpc', auth='public', readonly=True)
    def get_self_ordering_relations(self, self_order_config_id):
        pos_config, _ = self._verify_entry_access(self_order_config_id)
        return pos_config.load_data_params()

    @http.route(["/pos-self/<config_id>", "/pos-self/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def start_self_ordering(self, config_id=None, access_token=None, table_identifier=None, subpath=None):
        """ Backward compatibility because some customer have printed QR codes """
        if access_token:
            config_access_token = True
            pos_config = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ('access_token', '=', access_token)], limit=1)
        else:
            config_access_token = False
            pos_config = request.env["pos.config"].sudo().search([
                ("id", "=", config_id)], limit=1)

        self_order_config_id = pos_config.self_order_config_ids[0] if pos_config.self_order_config_ids else None
        if not self_order_config_id:
            raise werkzeug.exceptions.NotFound()

        access_token = self_order_config_id.access_token if config_access_token else None
        return self.start_new_self_ordering(str(self_order_config_id.id), access_token)

    def _verify_entry_access(self, self_order_config_id=None, access_token=None, table_identifier=None):
        table_sudo = False

        if not self_order_config_id or not self_order_config_id.isnumeric():
            raise werkzeug.exceptions.NotFound()

        if access_token:
            config_access_token = True
            self_config_sudo = request.env["pos.self.order.config"].sudo().search([
                ("id", "=", self_order_config_id), ('pos_config_id.access_token', '=', access_token)], limit=1)
        else:
            config_access_token = False
            self_config_sudo = request.env["pos.self.order.config"].sudo().search([
                ("id", "=", self_order_config_id)], limit=1)

        if not self_config_sudo or self_config_sudo.ordering_mode == 'nothing':
            raise werkzeug.exceptions.NotFound()

        company = self_config_sudo.pos_config_id.company_id
        user = self_config_sudo.default_user_id
        self_config_sudo = self_config_sudo.sudo(False).with_company(company).with_user(user).with_context(allowed_company_ids=company.ids, lang=request.cookies.get('frontend_lang'))

        if not self_config_sudo:
            raise werkzeug.exceptions.NotFound()

        if self_config_sudo.pos_config_id.has_active_session and self_config_sudo.ordering_mode == 'mobile':
            if config_access_token:
                config_access_token = self_config_sudo.pos_config_id.access_token
            table_sudo = table_identifier and (
                request.env["restaurant.table"]
                .sudo()
                .search([("identifier", "=", table_identifier), ("active", "=", True)], limit=1)
            )
            if table_sudo and table_sudo.parent_id:
                table_sudo = table_sudo.parent_id
        elif self_config_sudo.ordering_mode == 'kiosk':
            if config_access_token:
                config_access_token = self_config_sudo.pos_config_id.access_token
        else:
            config_access_token = ''

        return self_config_sudo, config_access_token
