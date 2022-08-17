# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class PageProperties(models.TransientModel):
    _name = 'website.page.properties'
    _description = 'Intermediate wizard to update page properties'

    @api.model
    def default_get(self, default_fields):
        defaults = super(PageProperties, self).default_get(default_fields)
        res_id = self.env.context.get('active_id')
        website_page = self.env['website.page'].browse(res_id)
        if website_page:
            defaults['page_id'] = website_page
        return defaults

    page_id = fields.Many2one('website.page', ondelete='cascade')
    website_id = fields.Many2one('website', related="page_id.website_id")

    name = fields.Char(string='Page Name', related="page_id.name", readonly=False, required=True)
    url = fields.Char(string='Page URL', related="page_id.url", readonly=False)
    enable_redirect = fields.Boolean(string='Redirect Old URL')
    redirect_type = fields.Selection([('301', '301 Moved permanently'), ('302', '302 Moved temporarily')], default='302', string='Redirection Type', required=True)

    is_in_menu = fields.Boolean('Show in Top Menu', related="page_id.is_in_menu", readonly=False)
    is_homepage = fields.Boolean('Use as Homepage', related="page_id.is_homepage", readonly=False)
    website_indexed = fields.Boolean('Indexed', related="page_id.website_indexed", readonly=False)
    is_published = fields.Boolean('Published', related="page_id.is_published", readonly=False)
    date_publish = fields.Datetime('Publishing Date', related="page_id.date_publish", readonly=False)
    visibility = fields.Selection(related='page_id.visibility', readonly=False)
    visibility_password_display = fields.Char('Password', related="page_id.visibility_password_display", readonly=False)
    groups_id = fields.Many2many('res.groups', string='Authorized Groups', related="page_id.groups_id", readonly=False)

    url_change = fields.Boolean(help="Technical field (for UX related behaviour), used to check if URL updated", default=False, store=False)

    @api.onchange('url')
    def _onchange_url(self):
        self.url_change = '/' + slugify(self.url, max_length=1024, path=True) != self.page_id.url

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            website_page = self.env['website.page'].browse(int(vals['page_id']))
            website_page_vals = website_page.read()[0]
            if website_page:
                edit_vals = {key: value for key, value in vals.items() if key in website_page_vals and value != website_page_vals.get(key, False)}
                if vals.get('enable_redirect'):
                    edit_vals.update({
                        'enable_redirect': vals['enable_redirect'],
                        'redirect_type': vals['redirect_type']
                    })
                website_page.write(edit_vals)
        return super().create(vals_list)
