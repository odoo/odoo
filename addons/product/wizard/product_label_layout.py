# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    product_packaging_ids = fields.One2many('product.packaging', compute='_compute_product_packaging_ids')
    packaging_id = fields.Many2one('product.packaging', string="", domain="[('id', 'in', product_packaging_ids)]")
    extra_html = fields.Html('Extra Content', default='')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = columns.isdigit() and int(columns) or 1
                wizard.rows = rows.isdigit() and int(rows) or 1
            else:
                wizard.columns, wizard.rows = 1, 1

    @api.depends('product_ids', 'product_tmpl_ids')
    def _compute_product_packaging_ids(self):
        for wizard in self:
            wizard.product_packaging_ids = wizard.product_ids.packaging_ids | wizard.product_tmpl_ids.packaging_ids

    def _get_report_template(self):
        # Get layout grid
        xml_id = ''
        if self.print_format == 'dymo':
            xml_id = 'product.report_product_template_label_dymo'
        elif 'x' in self.print_format:
            xml_id = 'product.report_product_template_label_%sx%s' % (self.columns, self.rows)
            if 'xprice' not in self.print_format:
                xml_id += '_noprice'
        return xml_id

    def _get_quantity_by_packaging(self):
        if not self.packaging_id:
            return {}
        quantity_by_packaging = {self.packaging_id.id: self.custom_quantity}
        return {'quantity_by_packaging': quantity_by_packaging}

    def _get_quantity_by_product(self):
        if self.packaging_id:
            return {}
        product_ids = self.product_tmpl_ids.ids if self.product_tmpl_ids else self.product_ids.ids
        return {'quantity_by_product': dict.fromkeys(product_ids, self.custom_quantity)}

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))
        if not self.product_tmpl_ids and not self.product_ids:
            raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

        # Build data to pass to the report
        active_model = 'product.template' if self.product_tmpl_ids else 'product.product'
        data = {
            'active_model': active_model,
            'layout_wizard': self.id,
            'price_included': 'xprice' in self.print_format,
            **self._get_quantity_by_packaging(),
            **self._get_quantity_by_product(),
        }
        return data

    def process(self):
        self.ensure_one()
        data = self._prepare_report_data()
        xml_id = self._get_report_template()
        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action
