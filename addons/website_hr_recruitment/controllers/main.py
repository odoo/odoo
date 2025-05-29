# Part of Odoo. See LICENSE file for full copyright and licensing details.

import warnings

from collections import defaultdict, OrderedDict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import partial
from operator import itemgetter

from odoo import http, _
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import email_normalize, escape_psql
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


class WebsiteHrRecruitment(WebsiteForm):
    _jobs_per_page = 12

    def sitemap_jobs(env, rule, qs):
        if not qs or qs.lower() in '/jobs':
            yield {'loc': '/jobs'}

    @http.route([
        '/jobs',
        '/jobs/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_jobs, list_as_website_content=_lt("Jobs"))
    def jobs(self, country_id=None, all_countries=False, department_id=None, office_id=None, contract_type_id=None,
             is_remote=False, is_other_department=False, is_untyped=None,  industry_id=None, is_industry_untyped=False,
             noFuzzy=False, page=1, search=None, **kwargs):
        """ This method is returning the job page.
        It's filtering the jobs by the given parameters and compute the display values for the filters
        by contaminating the jobs with the other filters.
        """
        def job_filtering_condition(job, filter_to_disable=False):
            country_filter = country if (country and filter_to_disable != 'country_id') else None
            field_filters = {
                'department_id': department.id,
                'address_id': office.id,
                'industry_id': industry.id,
                'contract_type_id': contract_type.id,
            }

            all_fields = all(
                job[job_field].id == value
                for job_field, value in field_filters.items()
                if job_field != filter_to_disable and value
            )
            if not all_fields or (
                country_filter and not (
                    job.address_id and job.address_id.country_id == country
                )
            ):
                return False
            not_exist_filter = {
                'department_id': is_other_department,
                'address_id': is_remote and filter_to_disable != 'country_id',
                'industry_id': is_industry_untyped,
                'contract_type_id': is_untyped,
            }
            return all(
                not job[job_field]
                for job_field, value in not_exist_filter.items()
                if job_field != filter_to_disable and value
            )

        def compute_filter_selection_counters(filtered_jobs, grouping_field, key_getter):
            jobs_grouped = filtered_jobs.grouped(grouping_field)
            counter = OrderedDict({'all': len(filtered_jobs)} | {
                key_getter(field_value): len(jobs_in_group) for field_value, jobs_in_group in jobs_grouped.items()
            })
            if None in counter:
                counter.move_to_end(None)
            counter.move_to_end('all', last=False)
            return counter

        def get_filter_snippets_display_values(jobs):
            """this function is used to compute the display values for the filters
            by contaminating the jobs with the other filters.
            """
            counter_by_object_by_field = defaultdict(OrderedDict)
            fields_and_filters = {
                ('address_id', 'count_per_office'),
                ('department_id', 'count_per_department'),
                ('contract_type_id', 'count_per_employment_type'),
                ('industry_id', 'count_per_industry'),
            }
            for field, alias in fields_and_filters:
                filtered_jobs = jobs.filtered(partial(job_filtering_condition, filter_to_disable=field))
                counter_by_object_by_field[alias] = compute_filter_selection_counters(
                    filtered_jobs, field, lambda field_value: field_value or None)

            filtered_jobs = jobs.filtered(partial(job_filtering_condition, filter_to_disable='country_id'))
            counter_by_object_by_field['count_per_country'] = compute_filter_selection_counters(
                filtered_jobs, 'address_id',
                lambda address_id: address_id.country_id if address_id and address_id.country_id else None
            )
            return counter_by_object_by_field

        def to_int(query_arg):
            return int(query_arg) if query_arg and query_arg.isdigit() else False

        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
        website = request.website
        department = env['hr.department'].browse(to_int(department_id)).exists()
        country = env['res.country'].browse(to_int(country_id)).exists()
        office = env['res.partner'].browse(to_int(office_id)).exists()
        contract_type = env['hr.contract.type'].browse(to_int(contract_type_id)).exists().sudo()
        industry =  env['res.partner.industry'].browse(to_int(industry_id)).exists().sudo()

        if not (country or department or office or contract_type or all_countries) \
            and (code := request.geoip.country_code) \
                and (country := env['res.country'].search([('code', '=', code)], limit=1)):
            country_count = env['hr.job'].search_count(
                website.website_domain()
                & Domain('address_id.country_id', '=', country.id)
            )
            if not country_count:
                country = False

        _total_not_used, details, fuzzy_search_term = website._search_with_fuzzy(
            "jobs", search,
            limit=self._jobs_per_page * 50,
            order="is_published desc, sequence, no_of_recruitment desc",
            options={
                'displayDescription': True,
                'allowFuzzy': not noFuzzy,
            }
        )
        searched_jobs = details[0].get('results', env['hr.job']).sudo()
        job_filter_values = get_filter_snippets_display_values(searched_jobs)
        found_jobs = searched_jobs.filtered(job_filtering_condition)
        total = len(found_jobs)
        pager = website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            url_args=request.httprequest.args,
            total=total,
            page=page,
            step=self._jobs_per_page,
        )
        offset = pager['offset']
        jobs_to_display = found_jobs[offset:offset + self._jobs_per_page]
        return request.render("website_hr_recruitment.index", {
            'jobs': jobs_to_display,
            'country_id': country,
            'department_id': department,
            'office_id': office,
            'contract_type_id': contract_type,
            'industry_id': industry,
            'is_remote': is_remote,
            'is_other_department': is_other_department,
            'is_untyped': is_untyped,
            'is_industry_untyped': is_industry_untyped,
            'pager': pager,
            'search': fuzzy_search_term or search,
            'search_count': total,
            **job_filter_values,
        })

    @http.route('/jobs/add', type='jsonrpc', auth="user", website=True)
    def jobs_add(self, **kwargs):
        # avoid branding of website_description by setting rendering_bundle in context
        job = request.env['hr.job'].with_context(rendering_bundle=True).create({
            'name': _('Job Title'),
        })
        return f"/jobs/{request.env['ir.http']._slug(job)}"

    @http.route('''/jobs/detail/<model("hr.job"):job>''', type='http', auth="public", website=True, sitemap=True)
    def jobs_detail(self, job, **kwargs):
        redirect_url = f"/jobs/{request.env['ir.http']._slug(job)}"
        return request.redirect(redirect_url, code=301)

    @http.route('''/jobs/<model("hr.job"):job>''', type='http', auth="public", website=True, sitemap=True)
    def job(self, job, **kwargs):
        return request.render("website_hr_recruitment.detail", {
            'job': job,
            'main_object': job,
        })

    @http.route('''/jobs/apply/<model("hr.job"):job>''', type='http', auth="public", website=True, sitemap=True)
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        return request.render("website_hr_recruitment.apply", {
            'job': job,
            'error': error,
            'default': default,
        })

    @http.route('/website_hr_recruitment/check_recent_application', type='jsonrpc', auth="public", website=True)
    def check_recent_application(self, field, value, job_id):
        def refused_applicants_condition(applicant):
            return not applicant.active \
                and applicant.job_id.id == int(job_id) \
                and applicant.create_date >= (datetime.now() - relativedelta(months=6))

        field_domain = {
            'name': [('partner_name', '=ilike', escape_psql(value))],
            'email': [('email_normalized', '=', email_normalize(value))],
            'phone': [('partner_phone', '=', value)],
            'linkedin': [('linkedin_profile', '=ilike', escape_psql(value))],
        }.get(field, [])

        applications_by_status = http.request.env['hr.applicant'].sudo().search(Domain.AND([
            field_domain,
            [
                ('job_id.website_id', 'in', [http.request.website.id, False]),
                '|',
                    ('application_status', '=', 'ongoing'),
                    '&',
                        ('application_status', '=', 'refused'),
                        ('active', '=', False),
            ]
        ]), order='create_date DESC').grouped('application_status')
        refused_applicants = applications_by_status.get('refused', http.request.env['hr.applicant'])
        if any(applicant for applicant in refused_applicants if refused_applicants_condition(applicant)):
            return {
                'message':  _(
                    'We\'ve found a previous closed application in our system within the last 6 months.'
                    ' Please consider before applying in order not to duplicate efforts.'
                )
            }

        if 'ongoing' not in applications_by_status:
            return {'message': None}

        ongoing_application = applications_by_status.get('ongoing')[0]
        if ongoing_application.job_id.id == int(job_id):
            recruiter_contact = "" if not ongoing_application.user_id else _(
                ' In case of issue, contact %(contact_infos)s',
                contact_infos=", ".join(
                    [value for value in itemgetter('name', 'email', 'phone')(ongoing_application.user_id) if value]
                ))
            return {
                'message':  _(
                    'An application already exists for %(value)s.'
                    ' Duplicates might be rejected. %(recruiter_contact)s',
                    value=value,
                    recruiter_contact=recruiter_contact
                )
            }

        return {
            'message':  _(
                'We found a recent application with a similar name, email, phone number.'
                ' You can continue if it\'s not a mistake.'
            )
        }

    def extract_data(self, model_sudo, values):
        short_introduction = values.get("short_introduction", None)
        data = super().extract_data(model_sudo, values)
        if short_introduction:
            introduction_label = self.env._("Short introduction from applicant")
            data["custom"] = data["custom"].replace("short_introduction", introduction_label)
        return data

    def _should_log_authenticate_message(self, record):
        if record._name == "hr.applicant" and not request.session.uid:
            return False
        return super()._should_log_authenticate_message(record)
