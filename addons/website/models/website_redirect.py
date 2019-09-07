# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteRedirect(models.Model):
    _name = "website.redirect"
    _description = "Website Redirect"
    _order = "sequence, id"
    _rec_name = 'url_from'

    redirect_type = fields.Selection([('301', 'Moved permanently (301)'), ('302', 'Moved temporarily (302)')], string='Redirection Type', required=True, default="301")
    url_from = fields.Char('Redirect From', required=True)
    url_to = fields.Char('Redirect To', required=True)
    website_id = fields.Many2one('website', 'Website', ondelete='cascade')
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
