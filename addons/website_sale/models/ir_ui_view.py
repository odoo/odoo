# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get('data-oe-model')]
        field = el.get('data-oe-field')
        if (
            Model == self.env['product.template'] and
            field == 'website_description' and
            not Model.check_access_rights('write') and
            self.user_has_groups('website.group_website_publisher')
        ):
            self = self.sudo()
        super(IrUiView, self).save_embedded_field(el)
