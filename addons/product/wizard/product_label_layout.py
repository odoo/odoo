# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import BinaryBytes, file_open


class ProductLabelLayout(models.TransientModel):
    _name = 'product.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    @api.model
    def _get_zpl_label_placeholder(self):
        with file_open('product/static/img/zpl_label_placeholder.png', 'rb') as f:
            return BinaryBytes(f.read())

    barcode_format = fields.Selection([
        ('barcode', 'Barcode 1D'),
        ('qr', 'QR Code'),
    ], string="Type", default='barcode')
    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7', '2 x 7'),
        ('4x7', '4 x 7'),
        ('4x12', '4 x 12'),
        ('zpl', 'ZPL Labels'),
    ], string="Format", default='2x7', required=True)
    zpl_template = fields.Selection([
        ('normal', 'Normal (2.25" x 1.25")'),
        ('small', 'Small (1.25" x 1.00")'),
        ('alternative', 'Alternative (2.00" x 1.00")'),
        ('jewelry', 'Jewelry (2.20" x 0.50")'),
    ], string="ZPL Template", default='normal', required=True)
    zpl_preview = fields.Image('ZPL Preview', readonly=True, default=_get_zpl_label_placeholder)
    with_price = fields.Boolean('Print With Price', default=True)
    custom_quantity = fields.Integer('Copies', default=1, required=True)
    product_ids = fields.Many2many('product.product')
    product_tmpl_ids = fields.Many2many('product.template')
    product_uom_ids = fields.Many2many('product.uom')
    available_packaging_ids = fields.Many2many('uom.uom', compute='_compute_available_packaging_ids')
    packaging_id = fields.Many2one(
        'uom.uom',
        string='Packaging',
        domain="[('id', 'in', available_packaging_ids)]",
    )
    extra_html = fields.Html('Extra Content', default='')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    def _get_available_packagings(self):
        self.ensure_one()

        default_packaging = self.env['uom.uom'].browse(self.env.context.get('default_packaging_id'))
        products = self.product_ids | self.product_uom_ids.product_id
        templates = self.product_tmpl_ids | products.product_tmpl_id
        template_products = products or templates.product_variant_ids

        packagings = default_packaging
        if products:
            for product in products:
                seller_uom = product.seller_ids.filtered(
                    lambda seller: not seller.product_id or seller.product_id == product
                ).uom_id
                packagings |= product._get_available_uoms() | seller_uom
        else:
            for template in templates:
                packagings |= template._get_available_uoms() | template.seller_ids.uom_id

        Bom = self.env.get('mrp.bom')
        if Bom is not None and templates:
            finished_product_boms = Bom.search([
                '|',
                ('product_id', 'in', template_products.ids),
                '&',
                ('product_id', '=', False),
                ('product_tmpl_id', 'in', templates.ids),
            ])
            packagings |= finished_product_boms.uom_id

        return packagings

    @api.depends('product_ids', 'product_tmpl_ids', 'product_uom_ids')
    def _compute_available_packaging_ids(self):
        for wizard in self:
            wizard.available_packaging_ids = wizard._get_available_packagings()

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')
                wizard.columns = columns.isdigit() and int(columns) or 1
                wizard.rows = rows.isdigit() and int(rows) or 1
            else:
                wizard.columns, wizard.rows = 1, 1

    def _get_label_template_xml_id(self):
        self.ensure_one()
        label_size = self.zpl_template if self.print_format == 'zpl' else self.print_format
        return f'product.{self.barcode_format}_{label_size}_label'

    def _get_report_xml_id(self):
        self.ensure_one()
        if self.print_format == 'zpl':
            return 'product.report_product_template_label_zpl'
        if self.print_format == 'dymo':
            return 'product.action_report_product_label_dymo'
        return 'product.action_report_product_label_pdf'

    def _get_label_requests(self):
        self.ensure_one()

        records = self.product_uom_ids or self.product_tmpl_ids or self.product_ids
        if not records:
            raise UserError(_(
                "No product to print, if the product is archived please unarchive it "
                "before printing its label."
            ))

        return [{
            'product': record.product_id if self.product_uom_ids else record,
            'barcode_value': record.barcode,
            'copies': self.custom_quantity,
            'packaging': self.packaging_id,
        } for record in records]

    def _prepare_label_values(self, product, barcode_value, copies, packaging, secondary_text=''):
        self.ensure_one()

        display_product = product.with_context(display_default_code=False)
        currency = (self.pricelist_id.currency_id or product.currency_id) if self.with_price else False
        primary_value = ''
        unit_price = None
        if self.with_price:
            price = self.pricelist_id._get_product_price(product, 1, currency=currency, uom=packaging)
            primary_value = currency.format(price)
            if self.env['res.groups']._is_feature_enabled('product.group_show_uom_price') and product.base_unit_count and product.base_unit_name:
                unit_price = product._get_base_unit_price(price)

        return {
            'barcode_type': 'datamatrix' if self.barcode_format == 'qr' else 'barcode',
            'barcode_value': barcode_value or '',
            'barcode_text': barcode_value or '',
            'copies': copies,
            'extra_content': str(self.extra_html or ''),
            'name': display_product.display_name if product.is_product_variant else product.name,
            'primary_value': primary_value,
            'reference': product.default_code or '',
            'secondary_text': packaging.display_name if packaging else secondary_text,
            'secondary_value': currency.format(unit_price) if unit_price is not None else '',
            'secondary_value_suffix': f'/{product.base_unit_name}' if unit_price is not None else '',
        }

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        return self._get_report_xml_id(), {
            'labels': [
                self._prepare_label_values(**label_request)
                for label_request in self._get_label_requests()
            ],
            'label_template': self._get_label_template_xml_id(),
            'layout': {
                'rows': self.rows,
                'columns': self.columns,
            },
        }

    def _save_user_defaults(self):
        self.ensure_one()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set(self._name, 'barcode_format', self.barcode_format, user_id=self.env.uid)
        IrDefault.set(self._name, 'print_format', self.print_format, user_id=self.env.uid)

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        self._save_user_defaults()
        report_action.update({'close_on_report_download': True})
        return report_action
