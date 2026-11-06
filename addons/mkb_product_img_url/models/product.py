# -*- coding: utf-8 -*-
# Copyright 2020-23 Manish Kumar Bohra <manishkumarbohra@outlook.com>
# License LGPL-3 - See http://www.gnu.org/licenses/Lgpl-3.0.html
from odoo import models, fields, api,_
import requests
import base64


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    image_url = fields.Char(string='Image URL')

    @api.onchange('image_url')
    def get_image_from_url(self):
        """This method mainly use to get image from the url"""
        image = False
        if self.image_url:
            if "http://" in self.image_url or "https://" in self.image_url:
                image = base64.b64encode(requests.get(self.image_url).content)
            else:
                with open(self.image_url, 'rb') as file:
                    image = base64.b64encode(file.read())
        self.image_1920 = image

    @api.model
    def create(self, values):
        res = super(ProductTemplateInherit, self).create(values)
        for img in res:
            if 'image_url' in values:
                img.get_image_from_url()
        return res

    def write(self, value):

        rec = super(ProductTemplateInherit, self).write(value)
        for img in self:  #
            if 'image_url' in value:
                img.get_image_from_url()
        return rec


class ProductProductInherit(models.Model):
    _inherit = 'product.product'

    image_url = fields.Char(string='Image URL')

    @api.onchange('image_url')
    def get_image_from_url(self):
        """This method mainly use to get image from the url"""
        image = False
        if self.image_url:
            if "http://" in self.image_url or "https://" in self.image_url:
                image = base64.b64encode(requests.get(self.image_url).content)
            else:
                with open(self.image_url, 'rb') as file:
                    image = base64.b64encode(file.read())

        self.image_1920 = image

    @api.model
    def create(self, values):
        res = super(ProductProductInherit, self).create(values)
        for img in res:
            if 'image_url' in values:
                img.get_image_from_url()
        return res

    def write(self, value):
        rec = super(ProductProductInherit, self).write(value)
        for img in self:
            if 'image_url' in value:
                img.get_image_from_url()
        return rec
