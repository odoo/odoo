# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import zipfile
from io import BytesIO
from urllib.parse import unquote
from uuid import uuid4

import qrcode
import qrcode.image.svg
from werkzeug.urls import url_unquote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import split_every


class PosSelfOrderConfig(models.Model):
    _name = 'pos.self.order.config'
    _inherit = ["pos.load.mixin"]
    _inherits = {'pos.config': 'pos_config_id'}
    _description = (
        """
        Configuration of the self-ordering mode, which allows customers
        to place orders by themselves from their smartphone by scanning
        a QR code on the table.

        This model will be used to link a pos.config to the self-ordering
        configuration, which will allow to override some of the pos.config
        settings when the customer is in self-ordering mode.
        """
    )

    def _default_color(self):
        return self.env.company.email_secondary_color

    def _default_language(self):
        return self.env['res.lang'].search([('code', '=', self.env.lang)], limit=1)

    def __default_available_languages(self):
        return self.env['res.lang'].get_installed()

    def _default_user(self):
        users = self.env['res.users'].search(['|', ('company_ids', 'in', self.env.company.id), ('company_id', '=', False)])
        for user in users:
            if user.sudo().has_group('point_of_sale.group_pos_manager'):
                return user
        return False

    name = fields.Char(string='Name')
    access_token = fields.Char("Access Token", default=lambda self: uuid4().hex[:16])
    pos_config_id = fields.Many2one(
        'pos.config',
        string='Point of Sale',
        required=True,
        ondelete='cascade',
    )

    # These fields override the ones configured in linked pos.config
    available_preset_ids = fields.Many2many(
        'pos.preset',
        string="Presets",
    )
    available_category_ids = fields.Many2many(
        'pos.category',
        string="Categories",
    )
    available_custom_link_ids = fields.Many2many(
        'pos_self_order.custom_link',
        string="Home buttons",
    )

    # Self ordering related fields
    url = fields.Char(compute='_compute_self_ordering_url')
    has_paper = fields.Boolean('Has paper', default=True)
    primary_color = fields.Char(string='Color', default=_default_color)
    ordering_mode = fields.Selection(
        [('consultation', 'QR menu'), ('mobile', 'QR menu + Ordering'), ('kiosk', 'Kiosk')],
        string="Ordering Mode",
        default='consultation',
        help="Choose the self ordering mode",
        required=True,
    )
    service_mode = fields.Selection(
        [('counter', 'Pickup zone'), ('table', 'Table')],
        string="Service Mode",
        default="counter",
        required=True,
    )
    pay_after = fields.Selection(
        selection=[('meal', 'After the meal'), ('each', 'After placing the order')],
        string="Pay After",
        default='meal',
        help="Choose when the customer will pay",
        required=True,
    )
    default_language_id = fields.Many2one(
        'res.lang',
        string="Default Language",
        default=_default_language,
    )
    available_language_ids = fields.Many2many(
        'res.lang',
        string="Languages",
        default=__default_available_languages,
    )
    image_home_ids = fields.Many2many(
        'ir.attachment',
        string="Set home image",
        help="Image to display on the self order screen",
        bypass_search_access=True,
    )
    image_background_ids = fields.Many2many(
        'ir.attachment',
        string="Set background image",
        help="Image to be displayed in the background",
        relation='pos_self_order_config_ir_attachment_rel',
        bypass_search_access=True,
    )
    default_user_id = fields.Many2one(
        'res.users',
        string="Default User",
        help="Access rights of this user will be used when visiting self order website when no session is open.",
        default=_default_user,
    )

    _sql_constraints = [
        ('PoS Config Unique', 'UNIQUE(pos_config_id)', 'Each POS configuration can only be linked to one self-ordering configuration.'),
    ]

    @api.constrains('pos_config_id')
    def _constrain_pos_config_id(self):
        config_ids = self.env['pos.self.order.config'].search([('pos_config_id', '!=', False)])
        for record in self:
            filtered_config_ids = config_ids.filtered(lambda c: c != record and c.pos_config_id == record.pos_config_id)
            if filtered_config_ids:
                raise ValidationError(_("The POS configuration %s is already linked to another self-ordering configuration.") % record.pos_config_id.name)

    @api.constrains('default_user_id')
    def _check_default_user(self):
        for record in self:
            if (
                record.ordering_mode != 'nothing' and (
                not record.default_user_id or (
                record.default_user_id
                and not record.default_user_id.sudo().has_group("point_of_sale.group_pos_user")
                and not record.default_user_id.sudo().has_group("point_of_sale.group_pos_manager")))
            ):
                raise UserError(_("The Self-Order default user must be a POS user"))

    @api.depends('pos_config_id')
    def _compute_self_ordering_url(self):
        for record in self:
            record.url = record.get_base_url() + record._get_self_order_route()

    @api.onchange('default_language_id', 'available_language_ids')
    def _onchange_pos_self_order_kiosk_default_language(self):
        if self.default_language_id not in self.available_language_ids:
            self.available_language_ids = self.available_language_ids + self.default_language_id
        if not self.default_language_id and self.available_language_ids:
            self.default_language_id = self.available_language_ids[0]

    @api.onchange('service_mode')
    def _onchange_pos_self_order_service_mode(self):
        for record in self:
            if record.service_mode == 'counter':
                record.pay_after = "each"

    @api.onchange("pay_after", "ordering_mode")
    def _onchange_pos_self_order_pay_after(self):
        for record in self:
            if record.pay_after == "meal" and record.ordering_mode == 'kiosk':
                raise ValidationError(_("Only pay after each is available with kiosk mode."))

            if record.service_mode == 'counter' and record.ordering_mode == 'mobile':
                record.pay_after = "each"

    def _ensure_public_attachments(self):
        self.image_background_ids.write({'public': True})
        self.image_home_ids.write({'public': True})

    @api.model_create_multi
    def create(self, vals_list):
        self._prepare_self_order_splash_screen(vals_list, is_new=True)
        self_config_ids = super().create(vals_list)
        self_config_ids._ensure_public_attachments()
        self_config_ids._prepare_self_order_custom_btn()
        return self_config_ids

    def get_limited_product_count(self):
        return self.pos_config_id.get_limited_product_count()

    def _get_limited_partner_count(self):
        return self.pos_config_id._get_limited_partner_count()

    def _get_available_pricelists(self):
        return self.pos_config_id._get_available_pricelists()

    def _get_special_products(self):
        return self.pos_config_id._get_special_products()

    def write(self, vals):
        self._prepare_self_order_splash_screen([vals])
        for record in self:
            if vals.get('ordering_mode') == 'kiosk' or (vals.get('ordering_mode') == 'mobile' and vals.get('service_mode') == 'counter'):
                vals['pay_after'] = 'each'

            if (
                vals.get('ordering_mode') == 'mobile'
                and (
                    vals.get('service_mode') == 'counter'
                    or (record.service_mode == 'counter' and vals.get('service_mode') != 'table')
                )
            ):
                vals['pay_after'] = 'each'

            if vals.get('ordering_mode') == 'mobile' and vals.get('pay_after') == 'meal':
                vals['service_mode'] = 'table'

        res = super().write(vals)
        self._ensure_public_attachments()
        self._prepare_self_order_custom_btn()
        return res

    @api.model
    def _load_pos_self_data_fields(self, pos_config_id):
        return ['id', 'name', 'company_id', 'journal_id', 'payment_method_ids', 'limit_categories',
            'available_category_ids', 'iface_splitbill', 'module_pos_restaurant', 'receipt_header',
            'currency_id', 'floor_ids', 'fiscal_position_ids', 'receipt_footer', 'default_fiscal_position_id',
            'use_pricelist', 'module_pos_restaurant', 'rounding_method', 'cash_rounding',
            'only_round_cash_method', 'has_active_session', 'available_preset_ids', 'default_preset_id',
            'use_presets', 'iface_tax_included', 'preparation_printer_ids', 'default_receipt_printer_id',
            'receipt_printer_ids', 'use_order_printer', 'other_devices', 'current_session_id', 'pricelist_id',
            'available_pricelist_ids', 'url', 'has_paper', 'available_custom_link_ids', 'ordering_mode',
            'service_mode', 'pay_after', 'default_language_id', 'available_language_ids', 'image_home_ids',
            'image_background_ids', 'default_user_id', 'pos_config_id',
        ]

    def _load_self_data_models(self):
        return ['pos.config', 'pos.session', 'pos.preset', 'resource.calendar.attendance',
            'pos.order', 'pos.order.line', 'pos.payment', 'pos.payment.method', 'res.partner',
            'res.currency', 'pos.printer', 'pos.category', 'product.template', 'product.product',
            'product.combo', 'product.combo.item', 'res.company', 'account.tax', 'account.tax.group',
            'res.country', 'product.category', 'product.pricelist', 'product.pricelist.item', 'account.fiscal.position',
            'res.lang', 'product.attribute', 'product.attribute.custom.value', 'product.template.attribute.line',
            'product.template.attribute.value', 'product.tag', 'decimal.precision', 'uom.uom', 'pos_self_order.custom_link',
            'restaurant.floor', 'restaurant.table', 'account.cash.rounding', 'res.country', 'res.country.state',
            'mail.template', 'pos.product.template.snooze']

    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', config.id)]

    @api.model
    def _load_pos_self_data_read(self, records, config):
        read_records = super()._load_pos_self_data_read(records, config)
        if not read_records:
            return read_records
        record = read_records[0]
        record['_self_ordering_image_home_ids'] = config.image_home_ids.ids
        record['_self_ordering_image_background_ids'] = config.image_background_ids.ids
        record['_pos_special_products_ids'] = config._get_special_products().ids
        record['_self_order_pos'] = True
        return read_records

    def load_self_data(self):
        response = {}
        response['pos.self.order.config'] = self.env['pos.self.order.config']._load_pos_self_data_search_read(response, self)

        for model in self._load_self_data_models():
            try:
                response[model] = self.env[model]._load_pos_self_data_search_read(response, self)
            except AccessError:
                response[model] = []

        return response

    def load_data_params(self):
        response = {}
        fields = self._load_pos_self_data_fields(self)
        response['pos.self.order.config'] = {
            'fields': fields,
            'relations': self.env['pos.session']._load_pos_data_relations('pos.self.order.config', fields),
        }

        for model in self._load_self_data_models():
            fields = self.env[model]._load_pos_self_data_fields(self)
            response[model] = {
                'fields': fields,
                'relations': self.env['pos.session']._load_pos_data_relations(model, fields),
            }

        return response

    def _get_self_order_route(self, table_id: int | None = None) -> str:
        self.ensure_one()
        base_route = f"/pos-self-order/{self.id}"
        table_route = ''

        if self.ordering_mode == 'consultation':
            return base_route

        if self.ordering_mode == 'mobile':
            table = self.env['restaurant.table'].search(
                [('active', '=', True), ('id', '=', table_id)], limit=1,
            )

            if table:
                table_route = f"&table_identifier={table.identifier}"

        return f"{base_route}?access_token={self.access_token}{table_route}"

    def preview_self_order_app(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self._get_self_order_route(),
            'target': 'new',
        }

    def generate_qr_codes_page(self):
        '''
        Generate the data needed to print the QR codes page
        '''
        if self.ordering_mode == 'mobile' and self.pos_config_id.module_pos_restaurant:
            table_ids = self.pos_config_id.floor_ids.table_ids

            if not table_ids:
                raise ValidationError(_("In Self-Order mode, you must have at least one table to generate QR codes"))

            url = url_unquote(self._get_self_order_route(table_ids[0].id))
            name = table_ids[0].table_number
        else:
            url = url_unquote(self._get_self_order_route())
            name = ''

        return self.env.ref('pos_self_order.report_self_order_qr_codes_page').report_action(
            [], data={
                'pos_name': self.pos_config_id.name,
                'floors': [
                    {
                        'name': floor.get('name'),
                        'type': floor.get('type'),
                        'table_rows': list(split_every(3, floor['tables'], list)),
                    }
                    for floor in self.pos_config_id._get_qr_code_data()
                ],
                'table_mode': self.ordering_mode and self.pos_config_id.module_pos_restaurant and self.service_mode == 'table',
                'self_order': self.ordering_mode == 'mobile',
                'table_example': {
                    'name': name,
                    'decoded_url': url or '',
                },
            },
        )

    def _generate_excel(self, rows, headers):
        import xlsxwriter  # noqa: PLC0415
        with BytesIO() as buffer:
            with xlsxwriter.Workbook(buffer, {'in_memory': True}) as workbook:
                worksheet = workbook.add_worksheet()

                for col, header in enumerate(headers):
                    worksheet.write(0, col, header)
                for row_idx, row in enumerate(rows, start=1):
                    for col_idx, cell in enumerate(row):
                        worksheet.write(row_idx, col_idx, cell)
            return buffer.getvalue()

    def generate_qr_codes_zip(self):
        if not self.ordering_mode in ['mobile', 'consultation']:
            raise ValidationError(_("QR codes can only be generated in mobile or consultation mode."))

        qr_images = []
        excel_rows = []

        if self.pos_config_id.module_pos_restaurant:
            table_ids = self.pos_config_id.floor_ids.table_ids

            if not table_ids:
                raise ValidationError(_("In Self-Order mode, you must have at least one table to generate QR codes"))

            for row_num, table in enumerate(table_ids, start=1):
                table_number = table.table_number
                floor_name = table.floor_id.name
                url = url_unquote(self.pos_config_id._get_self_order_url(table.id))
                qr_images.append({
                    'images': self.pos_config_id._generate_single_qr_code__(url),
                    'name': f"{floor_name} - {table_number}",
                })
                excel_rows.append([self.pos_config_id.name, floor_name, table_number, url])
            headers = ['Pos config', 'Floor', 'Table id', 'Url shortened']
        else:
            url = url_unquote(self.pos_config_id._get_self_order_url())
            qr_images.append({
                'images': self.pos_config_id._generate_single_qr_code__(url),
                'name': 'generic',
            })
            excel_rows.append([self.pos_config_id.name, url])
            headers = ['Pos config', 'Url shortened']

        xlsx_content = self._generate_excel(excel_rows, headers)

        # Create a zip with all images in qr_images
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', 0) as zip_file:
            zip_file.writestr('Table_url.xlsx', xlsx_content)
            for index, qr_image in enumerate(qr_images):
                with zip_file.open(f"{qr_image['name']} ({index + 1}).png", 'w') as buf:
                    qr_image['images']['png'].save(buf, format='PNG')
                with zip_file.open(f"{qr_image['name']} ({index + 1}).svg", 'w') as buf:
                    buf.write(qr_image['images']['svg'].to_string())
        zip_buffer.seek(0)

        # Delete previous attachments
        self.env['ir.attachment'].search([
            ('name', '=', 'self_order_qr_code.zip'),
        ]).unlink()

        # Create an attachment with the zip
        attachment_id = self.env['ir.attachment'].create({
            'name': 'self_order_qr_code.zip',
            'type': 'binary',
            'raw': zip_buffer.read(),
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment_id.id}",
            'target': 'new',
        }

    def get_pos_qr_stands(self):
        """Redirect to the get the free stands with the data of QR codes for the current POS config"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'pos_qr_stands',
            'params': {
                'data': self.pos_config_id.get_pos_qr_order_data(),
            },
        }

    def update_access_tokens(self):
        self.ensure_one()
        self.pos_config_id._update_access_token()

    def _prepare_self_order_custom_btn(self):
        for record in self:
            exists = record.env['pos_self_order.custom_link'].search_count([
                ('self_order_config_ids', 'in', record.id),
                ('url', '=', f"/pos-self/{record.id}/products"),
            ])

            if not exists:
                record.env['pos_self_order.custom_link'].create({
                    'name': _('Order Now'),
                    'url': f"/pos-self/{record.id}/products",
                    'self_order_config_ids': [(4, record.id)],
                })

    @api.model
    def _prepare_self_order_splash_screen(self, vals_list, is_new=False):
        for vals in vals_list:
            if not vals.get('ordering_mode'):
                return True

            if not vals.get('image_home_ids'):
                vals['image_home_ids'] = [(0, 0, {
                    'name': image_name,
                    'type': 'url',
                    'url': f'/pos_self_order/static/img/{image_name}',
                    'res_model': 'pos.config',
                }) for image_name in ['landing_01.jpg', 'landing_02.jpg', 'landing_03.jpg']]

            if is_new and not vals.get('image_background_ids'):
                vals['image_background_ids'] = [(0, 0, {
                    'name': "background.jpg",
                    'type': 'url',
                    'url': '/pos_self_order/static/img/kiosk_background.jpg',
                    'res_model': 'pos.config',
                })]
        return True

    def _generate_single_qr_code__(self, url):  # noqa: PLW3201
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return {
            'png': qr.make_image(fill_color="black", back_color="transparent"),
            'svg': qr.make_image(fill_color="black", back_color="transparent", image_factory=qrcode.image.svg.SvgImage),
        }

    def get_pos_qr_order_data(self):

        url_form = "https://www.odoo.com/app/point-of-sale-restaurant-qr-code"

        table_data = []
        if self.self_ordering_mode not in ['mobile', 'consultation']:
            return {
                'success': False,
                'error': 'INVALID_SELF_ORDERING_MODE',
            }

        table_ids = None
        if self.pos_config_id.module_pos_restaurant:
            table_ids = self.floor_ids.table_ids

        if table_ids and self.self_ordering_mode == 'mobile':
            for table in table_ids:
                url = self._get_self_order_url(table.id)
                table_data.append({
                    'url': url,
                    'name': f"{table.floor_id.name} - {table.table_number}",
                    'images': self._generate_single_qr_code__(unquote(url)),
                })
        else:
            url = self._get_self_order_url()
            table_data.append({
                'url': url,
                'name': "generic",
                'images': self._generate_single_qr_code__(unquote(url)),
            })

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", 0) as zip_file:
            for index, qr_data in enumerate(table_data):
                with zip_file.open(f"{qr_data['name']} ({index + 1}).png", "w") as buf:
                    qr_data['images']['png'].save(buf, format="PNG")
                with zip_file.open(f"{qr_data['name']} ({index + 1}).svg", "w") as buf:
                    buf.write(qr_data['images']['svg'].to_string())
        zip_buffer.seek(0)

        return {
            'success': True,
            'table_data': table_data,
            'self_ordering_mode': self.self_ordering_mode,
            'db_name': self.env.cr.dbname,
            'redirect_url': url_form,
            'zip_archive': base64.b64encode(zip_buffer.read()).decode('utf-8'),
        }
