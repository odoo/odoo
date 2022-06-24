# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import mute_logger
from odoo.tools.translate import html_translate


class Job(models.Model):

    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.multi.mixin']

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_website_description(self):
        return self.env['ir.qweb']._render("website_hr_recruitment.default_website_description", raise_if_not_found=False)

    website_published = fields.Boolean(help='Set if the application is published on the website of the company.')
    website_description = fields.Html('Website description', translate=html_translate, sanitize_attributes=False, default=_get_default_website_description, prefetch=False, sanitize_form=False)

    def _compute_website_url(self):
        super(Job, self)._compute_website_url()
        for job in self:
            job.website_url = "/jobs/detail_apply/%s" % job.id

    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()

    def get_backend_menu_id(self):
        return self.env.ref('hr_recruitment.menu_hr_recruitment_root').id

    def open_website_url(self):
        action = super().open_website_url()
        action['target'] = 'new'
        return action
