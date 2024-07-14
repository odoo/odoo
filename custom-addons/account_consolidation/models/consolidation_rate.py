# -*- coding: utf-8 -*-

from odoo import models, fields


class ConsolidationRate(models.Model):
    _name = "consolidation.rate"
    _description = "Consolidation Rate"

    chart_id = fields.Many2one('consolidation.chart', required=True, string="Consolidation")
    company_id = fields.Many2one('res.company', required=True, string="Company")
    rate = fields.Float(required=True, default=1.0)
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)

    def get_rate_for(self, date, company_id=False, chart_id=False):
        """
        Get the potential rate for a given company and a given chart at a given date
        :param date: the date
        :param company_id: the company on which this rate should be applied
        :type company_id: int
        :param chart_id: the consolidation chart on which this rate should be applied
        :type chart_id: int
        :return: the found rate or False
        :rtype: float|bool
        """
        domain = [
            ('date_start', '<=', date),
            ('date_end', '>=', date),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        if chart_id:
            domain.append(('chart_id', '=', chart_id))
        res = self.search_read(domain, ['rate'], limit=1, order='date_end desc')
        return res[0]['rate'] if len(res) > 0 else False
