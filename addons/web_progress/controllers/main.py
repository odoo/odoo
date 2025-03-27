import json
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.report import ReportController

class WPReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None, token=None):
        """
        Get web progress code from the context
        """
        parsed_context = json.loads(context or '{}')
        web_progress_obj = request.env['web.progress'].with_context(**parsed_context)
        web_progress_obj.web_progress_percent(0, 'Report')
        ret = super(WPReportController, self).report_download(data, context, token)
        web_progress_obj.web_progress_percent(100, 'Report done')
        return ret