# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo.http import request, route
from odoo.fields import Domain
from odoo.addons.website_partner.controllers.main import WebsitePartnerPage

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


class WebsitePartnership(WebsitePartnerPage):
    _references_per_page = 40

    def _get_grades(self, grade, grade_domain):
        partner_obj = request.env['res.partner']

        # Group by grade
        grade_groups = partner_obj.sudo()._read_group(
            grade_domain, ["grade_id"], ["__count"], order="grade_id")

        grades = [{
            'grade_id_count': sum(count for __, count in grade_groups),
            'grade_id': (0, ""),
            'active': grade is None,
        }]
        for g_grade, count in grade_groups:
            grades.append({
                'grade_id_count': count,
                'grade_id': (g_grade.id, g_grade.display_name),
                'active': grade and grade.id == g_grade.id,
            })
        return grades

    def _get_partners(self, base_partner_domain_post, pager, references_per_page=20, search_order=""):
        # search partners matching current search parameters
        partner_ids = request.env['res.partner'].sudo().search(
            base_partner_domain_post, order=search_order,
            offset=pager['offset'], limit=references_per_page)
        return partner_ids.sudo()

    def _get_base_partner_domain(self, search, searched_fields=()):
        base_partner_domain = Domain.AND([
            Domain('grade_id', '!=', False),
            Domain('website_published', '=', True),
            Domain('grade_id.active', '=', True),
        ])
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            base_partner_domain = Domain.AND([base_partner_domain, Domain('grade_id.website_published', '=', True)])
        if request.website.is_view_active("website_partnership.search_setting") and search:
            base_partner_domain = Domain.AND([base_partner_domain, Domain.OR(
                Domain(field, 'ilike', search)
                for field in searched_fields
            )])
        if request.website.is_view_active("website_partnership.companies_only_setting"):
            base_partner_domain = Domain.AND([base_partner_domain, Domain('is_company', '=', True)])
        return base_partner_domain

    def _get_partners_detail_values(self, partner_id, **post):
        values = super()._get_partners_detail_values(partner_id, **post)
        if grade_id := post.get('grade_id'):
            values.update({'current_grade': request.env['res.partner.grade'].browse(int(grade_id)).exists()})
        return values

    def _get_partners_values(self, grade=None, page=0, references_per_page=20, **post):
        search = post.get('search', "")

        base_partner_domain = self._get_base_partner_domain(search, searched_fields=('name', 'website_description'))

        grades = self._get_grades(grade, list(base_partner_domain))

        # current search, modify the base_partner_domain
        if request.website.is_view_active("website_partnership.categories_setting") and grade:
            base_partner_domain = Domain.AND([base_partner_domain, Domain('grade_id', '=', grade.id)])

        # format pager
        slug = request.env['ir.http']._slug
        url = '/partners'
        if grade:
            url += '/grade/' + slug(grade)
        url_args = {}
        if search:
            url_args['search'] = search
        partner_count = request.env['res.partner'].sudo().search_count(base_partner_domain)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=references_per_page, scope=7,
            url_args=url_args)

        partners = self._get_partners(base_partner_domain, pager, references_per_page=references_per_page, search_order="complete_name ASC, id ASC")

        values = {
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'pager': pager,
            'searches': post,
            'search_path': "%s" % werkzeug.urls.url_encode(post),
            'search': search,
        }
        return values

    @route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>',
        '/partners/grade/<model("res.partner.grade"):grade>/page/<int:page>',
    ], type='http', auth="public", website=True, readonly=True, list_as_website_content=_lt("Partners"))
    def partners(self, grade=None, page=0, **post):
        values = self._get_partners_values(
            grade=grade,
            page=page,
            references_per_page=self._references_per_page,
            **post
        )
        return request.render("website_partnership.index_layout", values)
