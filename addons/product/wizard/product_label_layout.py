# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_open


# Format table expressed as width x height in inch.
ZPL_FORMAT_SIZE = {
    'normal': (2.25, 1.25),
    'small': (1.25, 1.00),
    'alternative': (2.00, 1.00),
    'jewelry': (2.20, 0.50),
}

class ProductLabelLayout(models.TransientModel):
    _name = 'product.label.layout'
    _description = 'Choose the sheet layout to print the labels'

    @api.model
    def _get_zpl_label_placeholder(self):
        return base64.b64encode(file_open('product/static/img/zpl_label_placeholder.png', 'rb').read())

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7', '2 x 7'),
        ('4x7', '4 x 7'),
        ('4x12', '4 x 12'),
        ('zpl', 'ZPL Labels'),
    ], string="Format", default='2x7', required=True, store=True)
    with_price = fields.Boolean('Print With Price', default=True)
    zpl_template = fields.Selection([
        ('normal', 'Normal (2.25" x 1.25")'),
        ('small', 'Small (1.25" x 1.00")'),
        ('alternative', 'Alternative (2.00" x 1.00")'),
        ('jewelry', 'Jewelry (2.20" x 0.50")'),
    ], string="ZPL Template", default='normal', required=True)
    zpl_preview = fields.Image('ZPL Preview', readonly=True, default=_get_zpl_label_placeholder)
    custom_quantity = fields.Integer('Quantity', default=1, required=True)
    product_ids = fields.Many2many('product.product')
    product_tmpl_ids = fields.Many2many('product.template')
    extra_html = fields.Html('Extra Content', default='')
    rows = fields.Integer(compute='_compute_dimensions')
    columns = fields.Integer(compute='_compute_dimensions')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')
                wizard.columns = columns.isdigit() and int(columns) or 1
                wizard.rows = rows.isdigit() and int(rows) or 1
            else:
                wizard.columns, wizard.rows = 1, 1

    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))

        xml_id = f'product.report_product_template_label_{self.print_format}'

        active_model = ''
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'
        else:
            raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

        # Build data to pass to the report
        data = {
            'active_model': active_model,
            'quantity_by_product': {p: self.custom_quantity for p in products},
            'layout_wizard': self.id,
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
