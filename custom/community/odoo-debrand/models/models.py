# -*- coding: utf-8 -*-


from odoo import models, fields, api


class OdooDebrand(models.Model):
    _inherit = 'website'

    @api.one
    @api.depends('company_favicon')
    def get_favicon(self):
        self.favicon_url = 'data:image/png;base64,' + str(self.company_favicon)

    @api.one
    @api.depends('company_logo')
    def get_company_logo(self):
        self.company_logo_url = 'data:image/png;base64,' + str(self.company_logo)

    company_logo = fields.Binary("Logo", attachment=True,
                                 help="This field holds the image used for the Company Logo")
    company_name = fields.Char("Company Name", help="Branding Name")
    company_favicon = fields.Binary("Favicon", attachment=True,
                                    help="This field holds the image used for as favicon")
    company_website = fields.Char("Company URL")
    favicon_url = fields.Char("Url", compute='get_favicon')
    company_logo_url = fields.Char("Url", compute='get_company_logo')


class WebsiteConfig(models.TransientModel):
    _inherit = 'website.config.settings'

    company_logo = fields.Binary(related='website_id.company_logo', string="Company Logo",
                                 help="This field holds the image used for the Company Logo")
    company_name = fields.Char(related='website_id.company_name', string="Company Name")
    company_favicon = fields.Binary(related='website_id.company_favicon', string="Company Favicon",
                                    help="This field holds the image used for as favicon")
    company_website = fields.Char(related='website_id.company_website')
