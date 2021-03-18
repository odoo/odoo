# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    @api.model
    def _get_website_currency(self):
        pricelist = self.env['website'].get_current_website().get_current_pricelist()
        return pricelist.currency_id
<<<<<<< HEAD
=======

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model and model.model == 'product.product':
            data = [{
                'image_512': '/product/static/img/product_chair.png',
                'display_name': _('Chair'),
                'description_sale': _('Sit comfortably'),
            }, {
                'image_512': '/product/static/img/product_lamp.png',
                'display_name': _('Lamp'),
                'description_sale': _('Lightbulb sold separately'),
            }, {
                'image_512': '/product/static/img/product_product_20-image.png',
                'display_name': _('Whiteboard'),
                'description_sale': _('With three feet'),
            }, {
                'image_512': '/product/static/img/product_product_27-image.png',
                'display_name': _('Drawer'),
                'description_sale': _('On wheels'),
            }]
            merged = []
            for index in range(0, max(len(samples), len(data))):
                merged.append({**samples[index % len(samples)], **data[index % len(data)]})
                # merge definitions
            samples = merged
        return samples
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
