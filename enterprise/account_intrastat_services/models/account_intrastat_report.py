# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import SQL


class AccountIntrastatServicesReportHandler(models.AbstractModel):
    _name = 'account.intrastat.services.report.handler'
    _inherit = 'account.intrastat.report.handler'
    _description = 'Intrastat Services Report Custom Handler'

    def _get_intrastat_report_query(self, report, options, current_groupby, query_params=None, offset=None, limit=None, warnings=None, order_by=True):
        query_params = {
            **(query_params or {}),
            'product_type_condition': SQL("AND prodt.type = 'service'"),
            'commodity_warning_suffix': SQL('services'),
        }
        return super()._get_intrastat_report_query(report, options, current_groupby, query_params, offset, limit, warnings, order_by)
