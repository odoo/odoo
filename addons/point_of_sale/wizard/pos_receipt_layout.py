import json

from odoo import api, fields, models, _


class PosReceiptLayout(models.TransientModel):
    _name = 'pos.receipt.layout'
    _description = 'POS Receipt Layout'

    pos_config_id = fields.Many2one('pos.config', string='Point of Sale', required=True)
    receipt_layout = fields.Selection(related='pos_config_id.receipt_layout', readonly=False, required=True)
    receipt_logo = fields.Binary(related='pos_config_id.receipt_logo', readonly=False)
    receipt_bg_layout = fields.Selection(related='pos_config_id.receipt_bg_layout', readonly=False)
    receipt_bg_image = fields.Binary(related='pos_config_id.receipt_bg_image', readonly=False)
    receipt_header = fields.Html(related='pos_config_id.receipt_header', readonly=False)
    receipt_footer = fields.Html(related='pos_config_id.receipt_footer', readonly=False)
    receipt_font = fields.Selection(related='pos_config_id.receipt_font', readonly=False)
    receipt_preview = fields.Html(compute='_compute_receipt_preview', sanitize=False)
    basic_receipt_preview = fields.Boolean(string='Basic Receipt Preview')

    @api.depends('receipt_layout', 'receipt_logo', 'receipt_bg_layout', 'receipt_bg_image', 'receipt_header', 'receipt_footer', 'receipt_font', 'basic_receipt_preview')
    def _compute_receipt_preview(self):
        for wizard in self:
            preview_props = wizard._get_preivew_data()
            wizard.receipt_preview = wizard.env['ir.ui.view']._render_template(
                'point_of_sale.pos_receipt_layout_preview',
                {
                    'title': 'POS Receipt Preview',
                    'props': json.dumps(preview_props)
                }
            )

    def _get_preivew_data(self):
        company_data = self.pos_config_id.company_id.read(['id', 'phone', 'email', 'website', 'street', 'city', 'state_id', 'zip'])[0]

        config_data = {
            'id': self.pos_config_id.id,
            'receipt_layout': self.receipt_layout,
            'receipt_logo': self.receipt_logo and self.receipt_logo.decode('utf-8'),
            'receipt_bg_layout': self.receipt_bg_layout,
            'receipt_bg_image': self.receipt_bg_image and self.receipt_bg_image.decode('utf-8'),
            'receipt_header': self.receipt_header,
            'receipt_footer': self.receipt_footer,
            'receipt_font': self.receipt_font,
            'currency_id': self.pos_config_id.currency_id.id,
        }
        return {
            'company_data': company_data,
            'config_data': config_data,
            'previewMode': True,
            'basic_receipt': self.basic_receipt_preview,
            'product_data': self._get_preview_products(),
        }

    def _get_preview_products(self):
        excluded_product_ids = self.env['pos.config']._get_special_products().product_tmpl_id.ids
        unit_uom = self.env.ref('uom.product_uom_unit')
        domain = [('id', 'not in', excluded_product_ids), ('list_price', 'not in', [0.0])]
        if self.pos_config_id.iface_available_categ_ids:
            domain += [('pos_categ_ids', 'in', self.pos_config_id.iface_available_categ_ids.ids)]
        return self.env['product.template'].search_read(domain, ['name', 'list_price', 'uom_id'], limit=4) or [
            {'id': 5, 'name': _('Margarita Pizza'), 'list_price': 11.35, 'uom_id': [unit_uom.id, unit_uom.name]},
            {'id': 2, 'name': _('Apple Pie'), 'list_price': 13.0, 'uom_id': [unit_uom.id, unit_uom.name]},
            {'id': 3, 'name': _('Chees Burger'), 'list_price': 12.2, 'uom_id': [unit_uom.id, unit_uom.name]},
        ]

    def receipt_layout_save(self):
        return {'type': 'ir.actions.act_window_close'}
