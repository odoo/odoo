# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools import mute_logger
from odoo.tools.translate import html_translate


class Job(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.multi.mixin']

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_website_description(self):
        return self.env['ir.qweb']._render("website_hr_recruitment.default_website_description", raise_if_not_found=False)

    website_published = fields.Boolean(help='Set if the application is published on the website of the company.')
    website_description = fields.Html(
        'Website description', translate=html_translate,
        default=_get_default_website_description, prefetch=False,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False)
    job_details = fields.Html(
        'Process Details',
        translate=True,
        help="Complementary information that will appear on the job submission page",
        sanitize_attributes=False,
        default="""
            <span class="text-muted small">Time to Answer</span>
            <h6>2 open days</h6>
            <span class="text-muted small">Process</span>
            <h6>1 Phone Call</h6>
            <h6>1 Onsite Interview</h6>
            <span class="text-muted small">Days to get an Offer</span>
            <h6>4 Days after Interview</h6>
        """)

    @api.onchange('website_published')
    def _onchange_website_published(self):
        if self.website_published:
            self.is_published = True
        else:
            self.is_published = False

    def _compute_website_url(self):
        super(Job, self)._compute_website_url()
        for job in self:
            job.website_url = f'/jobs/detail/{slug(job)}'

    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()

    def get_backend_menu_id(self):
        return self.env.ref('hr_recruitment.menu_hr_recruitment_root').id

    def toggle_active(self):
        self.filtered('active').website_published = False
        return super().toggle_active()
