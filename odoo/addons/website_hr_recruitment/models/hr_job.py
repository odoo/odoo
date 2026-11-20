# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools import mute_logger
from odoo.tools.translate import html_translate


class Job(models.Model):
    _name = 'hr.job'
    _inherit = [
        'hr.job',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_description(self):
        return self.env['ir.qweb']._render('website_hr_recruitment.default_description', raise_if_not_found=False)

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_website_description(self):
        return self.env['ir.qweb']._render("website_hr_recruitment.default_website_description", raise_if_not_found=False)

    def _get_default_job_details(self):
        return _("""
            <span class="text-muted small">Time to Answer</span>
            <h6>2 open days</h6>
            <span class="text-muted small">Process</span>
            <h6>1 Phone Call</h6>
            <h6>1 Onsite Interview</h6>
            <span class="text-muted small">Days to get an Offer</span>
            <h6>4 Days after Interview</h6>
        """)

    description = fields.Html(
        'Job Description', translate=html_translate,
        default=_get_default_description, prefetch=False,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False)
    website_published = fields.Boolean(help='Set if the application is published on the website of the company.', tracking=True)
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
        default=_get_default_job_details)
    published_date = fields.Date(compute='_compute_published_date', store=True)

    @api.depends('website_published')
    def _compute_published_date(self):
        for job in self:
            job.published_date = job.website_published and fields.Date.today()

    @api.onchange('website_published')
    def _onchange_website_published(self):
        if self.website_published:
            self.is_published = True
        else:
            self.is_published = False

    def _compute_website_url(self):
        super(Job, self)._compute_website_url()
        for job in self:
            job.website_url = f'/jobs/{slug(job)}'

    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()

    def get_backend_menu_id(self):
        return self.env.ref('hr_recruitment.menu_hr_recruitment_root').id

    def toggle_active(self):
        self.filtered('active').website_published = False
        return super().toggle_active()

    @api.model
    def _search_get_detail(self, website, order, options):
        requires_sudo = False
        with_description = options['displayDescription']
        country_id = options.get('country_id')
        department_id = options.get('department_id')
        office_id = options.get('office_id')
        contract_type_id = options.get('contract_type_id')
        is_remote = options.get('is_remote')
        is_other_department = options.get('is_other_department')
        is_untyped = options.get('is_untyped')

        domain = [website.website_domain()]
        if country_id:
            domain.append([('address_id.country_id', '=', int(country_id))])
            requires_sudo = True
        if department_id:
            domain.append([('department_id', '=', int(department_id))])
        elif is_other_department:
            domain.append([('department_id', '=', None)])
        if office_id:
            domain.append([('address_id', '=', int(office_id))])
        elif is_remote:
            domain.append([('address_id', '=', None)])
        if contract_type_id:
            domain.append([('contract_type_id', '=', int(contract_type_id))])
        elif is_untyped:
            domain.append([('contract_type_id', '=', None)])

        if requires_sudo and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            # Rule must be reinforced because of sudo.
            domain.append([('website_published', '=', True)])


        search_fields = ['name']
        fetch_fields = ['name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate':  False},
        }
        if with_description:
            search_fields.append('description')
            fetch_fields.append('description')
            mapping['description'] = {'name': 'description', 'type': 'text', 'html': True, 'match': True}
        return {
            'model': 'hr.job',
            'requires_sudo': requires_sudo,
            'base_domain': domain,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-briefcase',
        }
