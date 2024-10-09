# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import base64
from os.path import join as opj
from typing import Optional, List, Dict
from werkzeug.urls import url_quote
from odoo.exceptions import UserError, ValidationError, AccessError

from odoo import api, fields, models, _, service
from odoo.tools import file_open, split_every


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _self_order_kiosk_default_languages(self):
        return self.env["res.lang"].get_installed()

    def _self_order_default_user(self):
        users = self.env["res.users"].search(['|', ('company_ids', 'in', self.env.company.id), ('company_id', '=', False)])
        for user in users:
            if user.sudo().has_group("point_of_sale.group_pos_manager"):
                return user

    status = fields.Selection(
        [("inactive", "Inactive"), ("active", "Active")],
        string="Status",
        compute="_compute_status",
        store=False,
    )
    self_ordering_url = fields.Char(compute="_compute_self_ordering_url")
    self_ordering_takeaway = fields.Boolean("Self Takeaway")
    self_ordering_mode = fields.Selection(
        [("nothing", "Disable"), ("consultation", "QR menu"), ("mobile", "QR menu + Ordering"), ("kiosk", "Kiosk")],
        string="Self Ordering Mode",
        default="nothing",
        help="Choose the self ordering mode",
        required=True,
    )
    self_ordering_service_mode = fields.Selection(
        [("counter", "Pickup zone"), ("table", "Table")],
        string="Self Ordering Service Mode",
        default="counter",
        help="Choose the kiosk mode",
        required=True,
    )
    self_ordering_default_language_id = fields.Many2one(
        "res.lang",
        string="Default Language",
        help="Default language for the kiosk mode",
        default=lambda self: self.env["res.lang"].search(
            [("code", "=", self.env.lang)], limit=1
        ),
    )
    self_ordering_available_language_ids = fields.Many2many(
        "res.lang",
        string="Available Languages",
        help="Languages available for the kiosk mode",
        default=_self_order_kiosk_default_languages,
    )
    self_ordering_image_home_ids = fields.Many2many(
        'ir.attachment',
        string="Add images",
        help="Image to display on the self order screen",
    )
    self_ordering_default_user_id = fields.Many2one(
        "res.users",
        string="Default User",
        help="Access rights of this user will be used when visiting self order website when no session is open.",
        default=_self_order_default_user,
    )
    self_ordering_pay_after = fields.Selection(
        selection=lambda self: self._compute_selection_pay_after(),
        string="Pay After:",
        default="meal",
        help="Choose when the customer will pay",
        required=True,
    )
    self_ordering_image_brand = fields.Image(
        string="Self Order Kiosk Image Brand",
        help="Image to display on the self order screen",
        max_width=1200,
        max_height=250,
    )
    self_ordering_image_brand_name = fields.Char(
        string="Self Order Kiosk Image Brand Name",
        help="Name of the image to display on the self order screen",
    )
    has_paper = fields.Boolean("Has paper", default=True)

    def _update_access_token(self):
        self.access_token = uuid.uuid4().hex[:16]
        self.floor_ids.table_ids._update_identifier()

    @api.model_create_multi
    def create(self, vals_list):
        self._prepare_self_order_splash_screen(vals_list)
        pos_config_ids = super().create(vals_list)
        pos_config_ids._prepare_self_order_custom_btn()
        return pos_config_ids

    @api.model
    def _prepare_self_order_splash_screen(self, vals_list):
        for vals in vals_list:
            if not vals.get('self_ordering_mode'):
                return True

            if not vals.get('self_ordering_image_home_ids'):
                vals['self_ordering_image_home_ids'] = [(0, 0, {
                    'name': image_name,
                    'datas': base64.b64encode(file_open(opj("pos_self_order/static/img", image_name), "rb").read()),
                    'res_model': 'pos.config',
                    'type': 'binary',
                }) for image_name in ['landing_01.jpg', 'landing_02.jpg', 'landing_03.jpg']]

        return True

    def _prepare_self_order_custom_btn(self):
        for record in self:
            exists = record.env['pos_self_order.custom_link'].search_count([
                ('pos_config_ids', 'in', record.id),
                ('url', '=', f'/pos-self/{record.id}/products')
            ])

            if not exists:
                record.env['pos_self_order.custom_link'].create({
                    'name': _('Order Now'),
                    'url': f'/pos-self/{record.id}/products',
                    'pos_config_ids': [(4, record.id)],
                })

    def write(self, vals):
        self._prepare_self_order_splash_screen([vals])

        for record in self:
            if vals.get('self_ordering_mode') == 'kiosk' or (vals.get('pos_self_ordering_mode') == 'mobile' and vals.get('pos_self_ordering_service_mode') == 'counter'):
                vals['self_ordering_pay_after'] = 'each'

            if (not vals.get('module_pos_restaurant') and not record.module_pos_restaurant) and vals.get('self_ordering_mode') == 'mobile':
                vals['self_ordering_pay_after'] = 'each'

            if (vals.get('self_ordering_service_mode') == 'counter' or record.self_ordering_service_mode == 'counter') and vals.get('self_ordering_mode') == 'mobile':
                vals['self_ordering_pay_after'] = 'each'

            if vals.get('self_ordering_mode') == 'mobile' and vals.get('self_ordering_pay_after') == 'meal':
                vals['self_ordering_service_mode'] = 'table'

        res = super().write(vals)
        self._prepare_self_order_custom_btn()
        return res

    @api.depends("module_pos_restaurant")
    def _compute_self_order(self):
        for record in self:
            if not record.module_pos_restaurant and record.self_ordering_mode != 'kiosk':
                record.self_ordering_mode = 'nothing'

    def _compute_selection_pay_after(self):
        selection_each_label = _("Each Order")
        version_info = service.common.exp_version()['server_version_info']
        if version_info[-1] == '':
            selection_each_label = f"{selection_each_label} {_('(require Odoo Enterprise)')}"
        return [("meal", _("Meal")), ("each", selection_each_label)]

    @api.constrains('self_ordering_default_user_id')
    def _check_default_user(self):
        for record in self:
            if (
                record.self_ordering_mode != 'nothing' and (
                not record.self_ordering_default_user_id or (
                record.self_ordering_default_user_id
                and not record.self_ordering_default_user_id.sudo().has_group("point_of_sale.group_pos_user")
                and not record.self_ordering_default_user_id.sudo().has_group("point_of_sale.group_pos_manager")))
            ):
                raise UserError(_("The Self-Order default user must be a POS user"))

    @api.constrains("payment_method_ids", "self_ordering_mode")
    def _onchange_payment_method_ids(self):
        if any(record.self_ordering_mode == 'kiosk' and any(pm.is_cash_count for pm in record.payment_method_ids) for record in self):
            raise ValidationError(_("You cannot add cash payment methods in kiosk mode."))

    def _get_qr_code_data(self):
        self.ensure_one()

        table_qr_code = []
        if self.self_ordering_mode == 'mobile' and self.module_pos_restaurant and self.self_ordering_service_mode == 'table':
            table_qr_code.extend([{
                    'name': floor.name,
                    'type': 'table',
                    'tables': [
                        {
                            'identifier': table.identifier,
                            'id': table.id,
                            'name': table.table_number,
                            'url': self._get_self_order_url(table.id),
                        }
                        for table in floor.table_ids.filtered("active")
                    ]
                }
                for floor in self.floor_ids]
            )
        else:
            # Here we use "range" to determine the number of QR codes to generate from
            # this list, which will then be inserted into a PDF.
            table_qr_code.extend([{
                'name': _('Generic'),
                'type': 'default',
                'tables': [{
                    'id': i,
                    'url': self._get_self_order_url(),
                } for i in range(0, 6)]
            }])

        return table_qr_code

    def _get_self_order_route(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        base_route = f"/pos-self/{self.id}"
        table_route = ""

        if self.self_ordering_mode == 'consultation':
            return base_route

        if self.self_ordering_mode == 'mobile':
            table = self.env["restaurant.table"].search(
                [("active", "=", True), ("id", "=", table_id)], limit=1
            )

            if table:
                table_route = f"&table_identifier={table.identifier}"

        return f"{base_route}?access_token={self.access_token}{table_route}"

    def _get_self_order_url(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        return url_quote(self.get_base_url() + self._get_self_order_route(table_id))

    def preview_self_order_app(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self._get_self_order_route(),
            "target": "new",
        }

    def _get_self_ordering_attachment(self, images):
        encoded_images = []
        for image in images:
            encoded_images.append({
                'id': image.id,
                'data': image.sudo().datas.decode('utf-8'),
            })

            # Only one image is needed for the mobile mode
            if self.self_ordering_mode == 'mobile':
                break
        return encoded_images

    def _load_self_data_models(self):
        return ['pos.session', 'pos.order', 'pos.order.line', 'pos.payment', 'pos.payment.method', 'res.currency', 'pos.category', 'product.product', 'product.combo', 'product.combo.item',
            'res.company', 'account.tax', 'account.tax.group', 'pos.printer', 'res.country', 'product.pricelist', 'product.pricelist.item', 'account.fiscal.position', 'account.fiscal.position.tax',
            'res.lang', 'product.attribute', 'product.attribute.custom.value', 'product.template.attribute.line', 'product.template.attribute.value',
            'decimal.precision', 'uom.uom', 'pos.printer', 'pos_self_order.custom_link', 'restaurant.floor', 'restaurant.table', 'account.cash.rounding']

    def load_self_data(self):
        # Init our first record, in case of self_order is pos_config
        config_fields = self._load_pos_self_data_fields(self.id)
        response = {
            'pos.config': {
                'data': self.env['pos.config'].search_read([('id', '=', self.id)], config_fields, load=False),
                'fields': config_fields,
            }
        }
        response['pos.config']['data'][0]['_self_ordering_image_home_ids'] = self._get_self_ordering_attachment(self.self_ordering_image_home_ids)
        self.env['pos.session']._load_pos_data_relations('pos.config', response)

        # Classic data loading
        for model in self._load_self_data_models():
            try:
                response[model] = self.env[model]._load_pos_self_data(response)
                self.env['pos.session']._load_pos_data_relations(model, response)
            except AccessError as e:
                response[model] = {
                    'data': [],
                    'fields': self.env[model]._load_pos_self_data_fields(self.id),
                    'error': e.args[0]
                }

                self.env['pos.session']._load_pos_data_relations(model, response)

        return response

    def _split_qr_codes_list(self, floors: List[Dict], cols: int) -> List[Dict]:
        """
        :floors: the list of floors
        :cols: the number of qr codes per row
        """
        self.ensure_one()
        return [
            {
                "name": floor.get("name"),
                "rows_of_tables": list(split_every(cols, floor["tables"], list)),
            }
            for floor in floors
        ]

    def _compute_self_ordering_url(self):
        for record in self:
            record.self_ordering_url = record.get_base_url() + record._get_self_order_route()

    def action_close_kiosk_session(self):
        if self.current_session_id and self.current_session_id.order_ids:
            self.current_session_id.order_ids.filtered(lambda o: o.state not in ['paid', 'invoiced']).unlink()

        self._notify('STATUS', {'status': 'closed'})
        return self.current_session_id.action_pos_session_closing_control()

    def _compute_status(self):
        for record in self:
            record.status = 'active' if record.has_active_session else 'inactive'

    def action_open_wizard(self):
        self.ensure_one()

        if not self.current_session_id:
            session = self.env['pos.session'].create({'user_id': self.env.uid, 'config_id': self.id})
            session.set_opening_control(0, "")
            self._notify('STATUS', {'status': 'open'})

        ctx = dict(self._context, app_id='pos_self_order', footer=False)

        return {
            'res_model': 'pos.config',
            'type': 'ir.actions.client',
            'tag': 'install_kiosk_pwa',
            'target': 'new',
            'context': ctx
        }

    def get_kiosk_url(self):
        return self.self_ordering_url

    @api.model
    def load_onboarding_kiosk_scenario(self):
        if not bool(self.env.company.chart_template):
            return False

        journal, payment_methods_ids = self._create_journal_and_payment_methods()
        restaurant_categories = self.get_categories([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        not_cash_payment_methods_ids = self.env['pos.payment.method'].search([
            ('is_cash_count', '=', False),
            ('id', 'in', payment_methods_ids),
        ]).ids
        self.env['pos.config'].create({
            'name': _('Kiosk'),
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': not_cash_payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': restaurant_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'self_ordering_mode': 'kiosk',
        })
