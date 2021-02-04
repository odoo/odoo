# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class IndustryImage(models.Model):

    _name = "website.industry.image"
    _description = "Industry Image"

    industry_id = fields.Many2one('website.industry')
    name = fields.Char()
    url = fields.Char()

    @api.model
    def get_industry_images(self, industry_id):
        image_ids = self.env['website.industry.image'].search([('industry_id', '=', industry_id)])
        return [image_id.get_resource() for image_id in image_ids]

    def get_resource(self):
        return {
            'name': self.name,
            'url': self.url
        }
