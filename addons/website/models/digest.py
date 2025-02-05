# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

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

    def _calculate_website_value_per_company(self, companies, start, end, get_value_per_website):
        """ Calculate the value per company by summing value of their website. """
        Website = self.env['website']
        websites_per_company = {
            company: Website.browse(website_ids)
            for company, website_ids in Website._read_group(
                [('company_id', 'in', companies.ids)],
                ['company_id'],
                ['id:array_agg'])}
        all_websites = Website.browse(
            list({website.id for websites in websites_per_company.values() for website in websites}))
        value_per_website = get_value_per_website(all_websites, start, end)
        return {company.id: sum(value_per_website.get(website, 0) for website in websites_per_company[company])
                for company in companies}

    @api.model
    def _website_kpi_website_track_count(self, companies, start, end):
        return self._calculate_website_value_per_company(
            companies, start, end, self._calculate_website_track_count), 'integer'

    @api.model
    def _website_kpi_website_visitors_count(self, companies, start, end):
        return self._calculate_website_value_per_company(
            companies, start, end, self._calculate_website_visitor_count), 'integer'
