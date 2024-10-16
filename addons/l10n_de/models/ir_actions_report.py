from odoo import models
from odoo.addons import account


class IrActionsReport(account.IrActionsReport):

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        data['din_header_spacing'] = report.get_paperformat().header_spacing
        return data
