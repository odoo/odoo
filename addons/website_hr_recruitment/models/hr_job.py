# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.website.structure_data_defination import SchemaBuilder
from odoo.tools import mute_logger
from odoo.tools.urls import urljoin as url_join
from odoo.tools.translate import html_translate


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = [
        'hr.job',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_website_description(self):
        return self.env['ir.qweb']._render("website_hr_recruitment.default_website_description", raise_if_not_found=False)

    @mute_logger('odoo.addons.base.models.ir_qweb')
    def _get_default_website_rating(self):
        return self.env['ir.qweb']._render("website_hr_recruitment.default_website_rating", raise_if_not_found=False)

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
        prefetch=False,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False,
        default='''
As an employee of our company, you will <b>collaborate with each department
to create and deploy disruptive products.</b> Come work at a growing company
that offers great benefits with opportunities to moving forward and learn
alongside accomplished leaders. We're seeking an experienced and outstanding
member of staff.
<br/><br/>
This position is both <b>creative and rigorous</b> by nature you need to think
outside the box. We expect the candidate to be proactive and have a "get it done"
spirit. To be successful, you will have solid solving problem skills.''')
    website_published = fields.Boolean(help='Set if the application is published on the website of the company.', tracking=True)
    website_description = fields.Html(
        'Website description', translate=html_translate,
        default=_get_default_website_description, prefetch=False,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False)
    website_rating = fields.Html(
        'Website rating', translate=html_translate,
        default=_get_default_website_rating, prefetch=False,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False)
    job_details = fields.Html(
        'Process Details',
        translate=True,
        help="Complementary information that will appear on the job submission page",
        sanitize_attributes=False,
        default=_get_default_job_details)
    full_url = fields.Char('job URL', compute='_compute_full_url')

    @api.depends('website_url')
    def _compute_full_url(self):
        for job in self:
            job.full_url = url_join(job.get_base_url(), (job.website_url or '/jobs'))

    @api.onchange('website_published')
    def _onchange_website_published(self):
        if self.website_published:
            self.is_published = True
        else:
            self.is_published = False

    def _compute_website_url(self):
        super()._compute_website_url()
        for job in self:
            # _slug call will fail with newId records.
            if not job.id:
                continue
            job.website_url = f'/jobs/{self.env["ir.http"]._slug(job)}'

    def set_open(self):
        self.write({'website_published': False, 'publish_on': False})
        return super().set_open()

    def get_backend_menu_id(self):
        return self.env.ref('hr_recruitment.menu_hr_recruitment_root').id

    def action_archive(self):
        self.filtered('active').write({'website_published': False, 'publish_on': False})
        return super().action_archive()

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

    def _to_structured_data(self):
        self.ensure_one()
        identifier = None
        # TODO: Add support for validThrough field
        valid_through = None
        employement_type = None
        if self.contract_type_id.sudo():
            employement_type = {
                'Permanent': 'FULL_TIME',
                'Temporary': 'TEMPORARY',
                'Interim': 'TEMPORARY',
                'Seasonal': 'TEMPORARY',
                'Full-Time': 'FULL_TIME',
                'Part-Time': 'PART_TIME',
                'Intern': 'INTERN',
                'Student': 'INTERN',
                'Apprenticeship': 'INTERN',
                'Thesis': 'INTERN',
                'Statutory': 'OTHER',
                'Employee': 'FULL_TIME',
            }.get(self.contract_type_id.sudo().name, 'OTHER')
        hiring_organization = None
        job_location = None
        if self.department_id:
            department_company = self.department_id.company_id.sudo()
            identifier = SchemaBuilder(
                "PropertyValue",
                name=department_company.name,
                value=f"{department_company.id}-{self.id}",
            )
            hiring_organization = self.website_id.organization_structured_data(department_company)
            job_location = SchemaBuilder(
                "Place",
                address=self.env['website'].postal_address_structured_data(department_company),
            )
        base_salary = None  # TODO: Add support for baseSalary field
        return SchemaBuilder(
            "JobPosting",
            title=self.name,
            url=self.full_url,
            description=self.website_description,
            date_posted=SchemaBuilder.datetime(self.create_date),
            valid_through=valid_through,
            direct_apply=True,
            employment_type=employement_type,
        ).add_nested(
            identifier=identifier,
            hiring_organization=hiring_organization,
            applicant_location_requirements=SchemaBuilder(
                "Country",
                name=self.address_id.country_id.code,
            ),
            job_location=job_location,
            base_salary=base_salary,
        )
