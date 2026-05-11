# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.website.helpers.jsonld_builder import JsonLd
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
        'website.structured_data.mixin',
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
        country_id = options.get('country_id')
        department_id = options.get('department_id')
        office_id = options.get('office_id')
        employee_type_id = options.get('employee_type_id')
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
        if employee_type_id:
            domain.append([('employee_type_id', '=', int(employee_type_id))])
        elif is_untyped:
            domain.append([('employee_type_id', '=', None)])

        if requires_sudo and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            # Rule must be reinforced because of sudo.
            domain.append([('website_published', '=', True)])

        search_fields = ['name', 'description']
        fetch_fields = ['name', 'website_url', 'description']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
            'search_item_metadata': {'name': 'address', 'type': 'text'},
            'description': {'name': 'description', 'type': 'text', 'html': True, 'match': True},
        }
        return {
            'model': 'hr.job',
            'requires_sudo': requires_sudo,
            'base_domain': domain,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-briefcase',
            'group_name': self.env._("Jobs"),
            'sequence': 90,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for data in results_data:
            job_address = self.browse(data['id']).sudo().address_id
            # sudo() to bypass access rights, since address_id is not available
            # to users in the public group.
            if job_address:
                data['address'] = ", ".join(filter(None, [
                    job_address.city,
                    job_address.state_id.name,
                    job_address.country_id.name,
                ]))
        return results_data

    def _get_jsonld(self, is_detail_page=False):
        """Return the list of JsonLd schemas for job post."""
        schemas = super()._get_jsonld(is_detail_page)
        if is_detail_page:
            schemas.append(self._build_job_post_jsonld())
            return schemas
        schemas.append(self._build_job_post_collectionpage_jsonld())
        return schemas

    def _get_breadcrumb_items(self, is_detail_page=False):
        """Return breadcrumb items for jobs listing and job detail pages."""
        items = super()._get_breadcrumb_items(is_detail_page)
        items.append((self.env._("Jobs"), "/jobs"))
        if is_detail_page:
            items.append((self.name, self.website_url))
        return items

    def _build_job_post_jsonld(self):
        """Build the detailed ``JobPosting`` schema for a job detail page."""
        self.ensure_one()
        job_post_jsonld = self._build_job_post_base_jsonld()
        job_post_jsonld.set({
            "directApply": True,
            "description": self.website_description,
        })
        nested_schema_data = {}
        if self.department_id and self.department_id.company_id:
            department_company = self.department_id.company_id
            nested_schema_data["identifier"] = JsonLd(
                "PropertyValue",
                {
                    "name": department_company.name,
                    "value": f"{department_company.id}-{self.id}",
                },
            )
        return job_post_jsonld.add_nested(nested_schema_data)

    def _build_job_post_base_jsonld(self):
        """Build the base ``JobPosting`` schema for listing cards."""
        self.ensure_one()
        base_url = self.get_base_url()
        location_type = 'ON_SITE' if self.address_id else 'TELECOMMUTE'
        contract_type = self.employee_type_id.sudo()
        schema_data = {
            "title": self.name,
            "url": f"{base_url}{self.website_url}",
            "description": self.description,
            "datePosted": JsonLd.to_iso_datetime(self.create_date),
            "jobLocationType": location_type,
            "totalJobOpenings": self.no_of_recruitment,
        }
        if contract_type:
            schema_data["employmentType"] = contract_type.name
        if self.department_id and self.department_id.name:
            schema_data["occupationalCategory"] = self.department_id.name

        nested_schema_data = {
            "hiringOrganization": JsonLd("Organization", {"@id": f"{base_url}/#organization"}),
        }
        country_code = self.company_id.country_id.code
        if country_code:
            nested_schema_data["applicantLocationRequirements"] = JsonLd(
                "Country",
                {"name": country_code},
            )

        # Public users cannot read partner addresses; sudo to safely access address fields.
        address_id = self.address_id.sudo()
        if address_id:
            place_nested_schema_data = {}
            if address_id.street:
                place_nested_schema_data["streetAddress"] = address_id.street
            if address_id.city:
                place_nested_schema_data["addressLocality"] = address_id.city
            if address_id.zip:
                place_nested_schema_data["postalCode"] = address_id.zip
            if address_id.state_id.code:
                place_nested_schema_data["addressRegion"] = address_id.state_id.code
            if address_id.country_id.code:
                place_nested_schema_data["addressCountry"] = address_id.country_id.code
            if place_nested_schema_data:
                nested_schema_data["jobLocation"] = JsonLd("Place").add_nested({
                    "address": JsonLd("PostalAddress", place_nested_schema_data),
                })
        return JsonLd("JobPosting", schema_data).add_nested(nested_schema_data)

    def _build_job_post_collectionpage_jsonld(self):
        """Build a ``CollectionPage`` schema for the job listing page."""
        website = self.env['website'].get_current_website()
        base_url = website.get_base_url()
        nested_schema_data = {
            "hasPart": [job._build_job_post_base_jsonld() for job in self],
            "isPartOf": JsonLd("Organization", {"@id": f"{base_url}/#organization"}),
        }
        return JsonLd("CollectionPage", {
            "name": self.env._("Jobs"),
            "url": f"{base_url}/jobs",
        }).add_nested(nested_schema_data)
