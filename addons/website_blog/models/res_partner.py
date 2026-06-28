# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    blog_post_ids = fields.One2many('blog.post', 'author_id', string="Blog Posts")
