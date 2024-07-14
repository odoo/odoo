# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self, date_start=False, date_stop=False, config_ids=False, session_ids=False
    ):
        data = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids
        )
        if session_ids:
            PF_list = []
            amount_PF = sum(PF_list.mapped('amount_total'))
            data["PF_number"] = len(PF_list)
            data["PF_Amount"] = amount_PF

        return data
