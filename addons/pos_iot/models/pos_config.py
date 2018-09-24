# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit='pos.config'

    def _compute_default_customer_html(self):
        return self.env['ir.qweb'].render('point_of_sale.customer_facing_display_html')

    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer.", default=False)
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration.", default=False)
    iface_customer_facing_display = fields.Boolean(string='Customer Facing Display', help="Show checkout to customers with a remotely-connected screen.", default=False)
    iface_print_via_proxy = fields.Boolean(string='Print via Proxy', help="Bypass browser printing and prints via the hardware proxy.", default=False)
    iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner.", default=False)
    customer_facing_display_html = fields.Html(string='Customer facing display content', translate=True, default=_compute_default_customer_html)
    
    iot_box_id = fields.Many2one('iot.box', string="IoTBox")
    proxy_ip = fields.Char(string='IP Address', related="iot_box_id.ip", store=True)

    @api.onchange('iface_print_via_proxy')
    def _onchange_iface_print_via_proxy(self):
        self.iface_print_auto = self.iface_print_via_proxy

    @api.onchange('iface_scan_via_proxy')
    def _onchange_iface_scan_via_proxy(self):
        if self.iface_scan_via_proxy:
            self.barcode_scanner = True
        else:
            self.barcode_scanner = False

    @api.onchange('module_pos_iot')
    def _onchange_module_pos_iot(self):
        if not self.module_pos_iot:
            self.iot_box_id = False
            self.proxy_ip=''
            self.iface_scan_via_proxy = False
            self.iface_electronic_scale = False
            self.iface_cashdrawer = False
            self.iface_print_via_proxy = False
            self.iface_customer_facing_display = False

    @api.multi
    def write(self, vals):
        config_display = self.filtered(lambda c: c.module_pos_iot and c.iface_customer_facing_display and not (c.customer_facing_display_html or '').strip())
        if config_display:
            super(PosConfig, config_display).write({'customer_facing_display_html': self._compute_default_customer_html()})

        return super(PosConfig, self).write(vals)

    @api.onchange('customer_facing_display_html')
    def _onchange_customer_facing_display_html(self):
        if self.iface_customer_facing_display and not self.customer_facing_display_html.strip():
            self.customer_facing_display_html = self._compute_default_customer_html()
