# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _name = 'product.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price')], string="Format", default='2x7xprice', required=True)
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    product_ids = fields.Many2many('product.product')
    product_tmpl_ids = fields.Many2many('product.template')
    product_uom_ids = fields.One2many('uom.uom', compute='_compute_product_packaging_ids')
    uom_id = fields.Many2one('uom.uom', domain="[('id', 'in', product_uom_ids)]")
    extra_html = fields.Html('Extra Content', default='')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    hide_uom_id = fields.Boolean(compute='_compute_hide_uom_id')
    hide_pricelist = fields.Boolean(compute='_compute_hide_pricelist')

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = columns.isdigit() and int(columns) or 1
                wizard.rows = rows.isdigit() and int(rows) or 1
            else:
                wizard.columns, wizard.rows = 1, 1

    @api.depends('uom_id')
    def _compute_hide_pricelist(self):
        for wizard in self:
            wizard.hide_pricelist = bool(wizard.uom_id)

    @api.depends('product_uom_ids')
    def _compute_hide_uom_id(self):
        for wizard in self:
            wizard.hide_uom_id = not bool(wizard.product_uom_ids)

    @api.depends('product_ids', 'product_tmpl_ids')
    def _compute_product_packaging_ids(self):
        for wizard in self:
            wizard.product_uom_ids = wizard.product_ids.uom_ids | wizard.product_tmpl_ids.uom_ids

    def _get_quantity_by_packaging(self, products):
        if not self.uom_id:
            return {}
        barcodes_by_product = {}
        product_uoms = self.env['product.uom'].search([
            ('product_id', 'in', products.ids),
            ('uom_id', '=', self.uom_id.id),
        ])
        for product in products:
            p_id = product.id
            product_uom = product_uoms.filtered(lambda p_uom: p_uom.product_id.id == p_id)[:1]
            barcodes_by_product[product_uom.id] = self.custom_quantity
        quantity_by_packaging = {self.uom_id.id: self.custom_quantity}
        return {'quantity_by_packaging': quantity_by_packaging}

    def _get_quantity_by_product(self):
        if self.uom_id:
            return {}
        product_ids = self.product_tmpl_ids.ids if self.product_tmpl_ids else self.product_ids.ids
        return {'quantity_by_product': dict.fromkeys(product_ids, self.custom_quantity)}

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        # Get layout grid
        if self.print_format == 'dymo':
            xml_id = 'product.report_product_template_label_dymo'
        elif 'x' in self.print_format:
            xml_id = 'product.report_product_template_label_%sx%s' % (self.columns, self.rows)
            if 'xprice' not in self.print_format:
                xml_id += '_noprice'
        else:
            xml_id = ''

        active_model = ''
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids
            active_model = 'product.product'
        else:
            raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

        data_by_product_id = defaultdict(list)
        product_uoms = self.env['product.uom']
        product_ids = (products if active_model == 'product.product' else products.product_variant_id).ids

        # If the user wants to print labels for a specific UoM,
        # fetch packagings for this UoM/product pair.
        product_uoms = self.env['product.uom'].search([
                ('product_id', 'in', product_ids),
                ('uom_id', '=', self.uom_id.id),
            ]) if self.uom_id else self.env['product.uom']

        for product in products:
            label_data = {
                'barcode': product.barcode or '',
                'quantity': self.custom_quantity or 1,
            }
            product_variant = product if active_model == 'product.product' else product.product_variant_id
            # # TODO BEFORE MERGING: to clarify with PO. The next portion of code enforces the selected UOM
            # # and so, if selected product has no compatible packaging, there will be no label to print.
            # # Current (not commented) code print the usual product's label instead.
            # # To check with PO to know which version we want.
            # # if self.uom_id:
            #     product_uom = product_uoms.filtered(lambda puom: puom.product_id == product_variant)[:1]
            #     data.update(
            #         packaging_id=product_uom.id,
            #         barcode=(product_uom.barcode or ''),
            #         uom_id=product_uom.uom_id.id,
            #     )
            product_uom = self.uom_id and product_uoms.filtered(lambda puom: puom.product_id == product_variant)[:1]
            if product_uom:
                label_data.update(
                    packaging_id=product_uom.id,
                    barcode=(product_uom.barcode or ''),
                    uom_id=product_uom.uom_id.id,
                )
            data_by_product_id[product.id].append(label_data)

        # Build data to pass to the report
        data = {
            'active_model': active_model,
            'data_by_product_id': data_by_product_id,
            'layout_wizard': self.id,
            'price_included': 'xprice' in self.print_format,
        }
        return xml_id, data

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action
