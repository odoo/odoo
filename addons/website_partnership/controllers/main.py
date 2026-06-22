# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.website.controllers.main import QueryURL
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

    def _get_partners(self, search, offset, limit, order, options):
        # search partners matching current search parameters
        partner_count, details, fuzzy_search_term = self.env.website._search_with_fuzzy(
            search_type='partners',
            search=search,
            offset=offset,
            limit=limit,
            order=order,
            options=options
        )
        partners = details[0].get('results')
        return partner_count, partners, fuzzy_search_term

    def _get_partners_search_options(self, grade=None, **post):
        return {
            'allowFuzzy': not post.get('noFuzzy'),
            'grade': request.env['ir.http']._slug(grade) if grade else None,
        }

    def _get_partners_detail_values(self, partner_id, **post):
        values = super()._get_partners_detail_values(partner_id, **post)
        if grade_id := post.get('grade_id'):
            values.update({'current_grade': request.env['res.partner.grade'].browse(int(grade_id)).exists()})
        return values

    def _get_partners_values(self, grade=None, page=1, references_per_page=20, **post):
        search = post.get('search', "")
        slug = request.env['ir.http']._slug
        options = self._get_partners_search_options(grade=grade, **post)
        order = 'is_published desc, %s, id desc' % post.get('order', "name ASC")
        partner_count, partners, fuzzy_search_term = self._get_partners(
            search=search,
            offset=(page - 1) * references_per_page,
            limit=references_per_page,
            order=order,
            options=options
        )
        search_details = self.env.website._search_get_details(search_type='partners', order=order, options={'allowFuzzy': not post.get('noFuzzy')})
        post['search'] = fuzzy_search_term or search
        final_search_domain = self.env.website._search_build_domain(
            domain_list=search_details[0].get('base_domain', []),
            search=fuzzy_search_term or search,
            fields=search_details[0].get('search_fields'),
            extra=search_details[0].get('search_extra', [])
        )
        grades = self._get_grades(grade, final_search_domain)
        pager = self.env.website.pager(
            url=f"/partners/grade/{slug(grade)}" if grade else "/partners",
            total=partner_count,
            page=page,
            step=references_per_page,
            scope=7,
            url_args=post
        )
        keep = QueryURL(
            '/partners',
            ['grade'],
            grade=grade,
            **{key: value for key, value in post.items() if (key == 'search')}
        )

        values = {
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'pager': pager,
            'searches': post,
            'search': search,
            'keep_partners_url': keep,
            'search_count': partner_count,
            'original_search': fuzzy_search_term and search,
        }
        return values

    @route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>',
        '/partners/grade/<model("res.partner.grade"):grade>/page/<int:page>',
    ], type='http', auth="public", website=True, readonly=True, list_as_website_content=_lt("Partners"))
    def partners(self, grade=None, page=1, **post):
        values = self._get_partners_values(
            grade=grade,
            page=page,
            references_per_page=self._references_per_page,
            **post
        )
        return request.render("website_partnership.index_layout", values)
