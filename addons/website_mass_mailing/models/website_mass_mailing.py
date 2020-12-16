# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingPopup(models.Model):
    _name = 'website.mass_mailing.popup'
    _description = "Mailing list popup"

    def _default_popup_content(self):
        return self.env['ir.ui.view']._render_template('website_mass_mailing.s_newsletter_subscribe_popup_content')

    mailing_list_id = fields.Many2one('mailing.list')
    website_id = fields.Many2one('website')
    popup_content = fields.Html(string="Website Popup Content", default=_default_popup_content, translate=True, sanitize=False)
