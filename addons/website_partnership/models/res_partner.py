# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.searchable.mixin']

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for partner, data in zip(self, results_data):
            data["image_url"] = self.env["website"].image_url(partner, "image_128")
        return results_data

    def _search_get_detail(self, website, order, options):
        grade = options.get("grade")
        country = options.get("country")

        base_domain = [
            [('grade_id', '!=', False)],
            [('website_published', '=', True)],
            [('grade_id.active', '=', True)],
        ]

        if not self.env.user.has_group("website.group_website_restricted_editor"):
            base_domain.append([('grade_id.website_published', '=', True)])
        if website.is_view_active("website_partnership.companies_only_setting"):
            base_domain.append([('is_company', '=', True)])
        if grade:
            base_domain.append([('grade_id', '=', self.env["ir.http"]._unslug(grade)[1])])
        if country:
            base_domain.append([('country_id', '=', self.env["ir.http"]._unslug(country)[1])])

        return {
            "model": "res.partner",
            "base_domain": base_domain,
            "search_fields": ["name", "website_description"],
            "fetch_fields": ["name", "website_url"],
            "mapping": {
                "name": {"name": "name", "type": "text", "match": True},
                "website_url": {"name": "website_url", "type": "text", "truncate": False},
                "image_url": {"name": "image_url", "type": "html"},
            },
            "icon": "fa-building",
            "order": order or "name asc, id desc",
            "group_name": self.env._("Partners"),
        }
