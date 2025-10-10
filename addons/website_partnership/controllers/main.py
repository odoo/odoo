# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo.http import request, route
from odoo.addons.website_partner.controllers.main import WebsitePartnerPage

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


class WebsitePartnership(WebsitePartnerPage):
    _references_per_page = 40

    def _get_partners_values(self, grade=None, page=0, references_per_page=20, **post):
        partner_obj = request.env['res.partner']

        search = post.get('search', '')

        base_partner_domain = [('grade_id', '!=', False), ('website_published', '=', True), ('grade_id.active', '=', True)]
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            base_partner_domain += [('grade_id.website_published', '=', True)]
        if search:
            base_partner_domain += ['|', ('name', 'ilike', search), ('website_description', 'ilike', search)]

        # Group by grade
        grade_domain = list(base_partner_domain)
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

        # current search
        if grade:
            base_partner_domain += [('grade_id', '=', grade.id)]

        # format pager
        slug = request.env['ir.http']._slug
        if grade:
            url = '/partners/grade/' + slug(grade)
        else:
            url = '/partners'
        url_args = {}
        if search:
            url_args['search'] = search

        partner_count = partner_obj.sudo().search_count(base_partner_domain)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=references_per_page, scope=7,
            url_args=url_args)

        # search partners matching current search parameters
        partner_ids = partner_obj.sudo().search(
            base_partner_domain, order="complete_name ASC, id ASC",
            offset=pager['offset'], limit=references_per_page)
        partners = partner_ids.sudo()
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
        return request.render("website_partnership.index_layout", values, status=values.get('partners') and 200 or 404)

    # Do not use semantic controller due to sudo()
    @route()
    def partners_detail(self, partner_id, **post):
        current_slug = partner_id
        _, partner_id = request.env['ir.http']._unslug(partner_id)
        current_grade = None
        grade_id = post.get('grade_id')
        if grade_id:
            current_grade = request.env['res.partner.grade'].browse(int(grade_id)).exists()
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(partner_id)
            is_website_restricted_editor = request.env.user.has_group('website.group_website_restricted_editor')
            if partner.exists() and (partner.website_published or is_website_restricted_editor):
                partner_slug = request.env['ir.http']._slug(partner)
                if partner_slug != current_slug:
                    return request.redirect('/partners/%s' % partner_slug)
                values = {
                    'main_object': partner,
                    'partner': partner,
                    'current_grade': current_grade,
                }
                return request.render("website_partnership.partner_page", values)
        raise request.not_found()
