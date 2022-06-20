# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_website_visitor_count = fields.Boolean('Visitors')
    kpi_website_visitor_count_value = fields.Integer(compute='_compute_kpi_website_visitors_count_value')
    kpi_website_track_count = fields.Boolean('Tracked Page Views')  # Non unique
    kpi_website_track_count_value = fields.Integer(compute='_compute_kpi_website_track_count_value')

    @api.model
    def _calculate_website_visitor_count(self, websites, start, end):
        """ Calculate the unique visitor count per website for the given period. """
        if len(websites) == 0:
            return dict()
        Website = self.env['website']
        self.env.cr.execute("""
            SELECT v.website_id, count(DISTINCT t.visitor_id)
              FROM website_track t
              JOIN website_visitor v ON v.id=t.visitor_id
             WHERE v.website_id IN %(website_ids)s AND t.visit_datetime >= %(start)s AND t.visit_datetime < %(end)s
          GROUP BY v.website_id
          """, params={'website_ids': tuple(websites.ids), 'start': start, 'end': end})
        return {Website.browse(website_id): count for website_id, count in self.env.cr.fetchall()}

    @api.model
    def _calculate_website_track_count(self, websites, start, end):
        """ Calculate the track count per website for the given period. """
        if len(websites) == 0:
            return dict()
        Website = self.env['website']
        self.env.cr.execute("""
            SELECT v.website_id, count(t.id)
              FROM website_track t
              JOIN website_visitor v ON v.id=t.visitor_id
             WHERE v.website_id IN %(website_ids)s AND t.visit_datetime >= %(start)s AND t.visit_datetime < %(end)s
          GROUP BY v.website_id
          """, params={'website_ids': tuple(websites.ids), 'start': start, 'end': end})
        return {Website.browse(website_id): count for website_id, count in self.env.cr.fetchall()}

    def _calculate_value_per_company(self, get_value_per_website):
        """ Calculate the value per company by summing value of their website. """
        self._raise_if_not_member_of('website.group_website_restricted_editor')
        Website = self.env['website']
        start, end, companies = self._get_kpi_compute_parameters()
        websites_per_company = {
            company: Website.browse(website_ids)
            for company, website_ids in Website._read_group(
                [('company_id', 'in', companies.ids)],
                ['company_id'],
                ['id:array_agg'])}
        all_websites = Website.browse(
            list({website.id for websites in websites_per_company.values() for website in websites}))
        value_per_website = get_value_per_website(all_websites, start, end)
        return {company: sum(value_per_website.get(website, 0) for website in websites_per_company[company])
                for company in companies}

    def _compute_kpi_website_track_count_value(self):
        self._raise_if_not_member_of('website.group_website_restricted_editor')
        value_per_company = self._calculate_value_per_company(self._calculate_website_track_count)
        for digest in self:
            company = digest.company_id or self.env.company
            digest.kpi_website_track_count_value = value_per_company.get(company, 0)

    def _compute_kpi_website_visitors_count_value(self):
        """ Compute the aggregated unique visitor of the websites company.
        Note that this computation relies on website_visitor which may create multiple visitor for the same user
        (indeed the user is not always identified).
        """
        self._raise_if_not_member_of('website.group_website_restricted_editor')
        value_per_company = self._calculate_value_per_company(self._calculate_website_visitor_count)
        for digest in self:
            company = digest.company_id or self.env.company
            digest.kpi_website_visitor_count_value = value_per_company.get(company, 0)

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('website.menu_website_configuration').id
        res['kpi_action']['kpi_website_visitor_count'] = f'website.website_visitors_action?menu_id={menu_id}'
        res['kpi_action']['kpi_website_track_count'] = f'website.website_visitor_view_action?menu_id={menu_id}'
        res['kpi_sequence']['kpi_website_visitor_count'] = 3500
        res['kpi_sequence']['kpi_website_track_count'] = 3505
        return res
