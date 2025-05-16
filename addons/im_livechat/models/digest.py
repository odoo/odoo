# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    @api.model
    def _im_livechat_kpi_livechat_rating(self, companies, start, end):
        channels = self.env['discuss.channel'].search([('channel_type', '=', 'livechat')])
        domain = [
            ('create_date', '>=', start),
            ('create_date', '<', end),
        ]
        ratings = channels.rating_get_grades(domain)
        value = (
            ratings['great'] * 100 / sum(ratings.values())
            if sum(ratings.values()) else 0
        )
        return {company.id: value for company in companies}, 'float'
