# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools.sql import drop_view_if_exists


class ReportIntrastat(models.Model):
    _inherit = 'report.intrastat'
    
    def _query(self):
        result = super(ReportIntrastat, self)._query()
        result['select'] += """,
            case when inv_line.intrastat_product_origin_country_id is null 
                then \'QU\' 
                else product_country.code 
                end AS intrastat_product_origin_country,
            case when partner_country.id is null 
                then \'QV999999999999\' 
                else partner.vat 
                end AS partner_vat
            """
        result['from'] += """ 
            left join res_partner partner ON inv_line.partner_id = partner.id
            left join res_country product_country ON product_country.id = inv_line.intrastat_product_origin_country_id
            left join res_country partner_country ON partner.country_id = partner_country.id AND partner_country.intrastat is true
            """
        result['group_by'] += """,
            inv_line.intrastat_product_origin_country_id, 
            product_country.code, 
            partner_country.id, 
            partner.vat
        """
        return result