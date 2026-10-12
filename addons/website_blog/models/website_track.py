# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    blog_post_id = fields.Many2one(
        comodel_name='blog.post', ondelete='cascade', readonly=True, index='btree_not_null',
    )
