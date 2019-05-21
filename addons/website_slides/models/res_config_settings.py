# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    website_slide_google_app_key = fields.Char(related='website_id.website_slide_google_app_key', readonly=False)
    
    module_website_slides_forum = fields.Boolean("Forum")
    mail_attendees = fields.Boolean("Mailing")
    module_website_slides_survey = fields.Boolean("Certification")
    module_website_sale_slides = fields.Boolean("Sell Courses")

    @api.multi
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            mail_attendees = self.env['ir.config_parameter'].sudo().get_param('website_slides.mail_param'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('website_slides.mail_param', self.mail_attendees)
        group_mail_attendees = self.env.ref('website_slides.group_mail_attendees', False)
        if self.mail_attendees:
            group_mail_attendees.write({'users': [(4, self.env.uid)]})
        else:
            group_mail_attendees.write({'users': [(3, self.env.uid)]})