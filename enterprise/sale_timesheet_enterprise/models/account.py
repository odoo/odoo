# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression

from odoo.addons.sale_timesheet_enterprise.models.sale import DEFAULT_INVOICED_TIMESHEET


class AccountInvoice(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _timesheet_domain_get_invoiced_lines(self, sale_line_delivery):
        domain = super(AccountInvoice, self)._timesheet_domain_get_invoiced_lines(sale_line_delivery)
        param_invoiced_timesheet = self.env['ir.config_parameter'].sudo().get_param('sale.invoiced_timesheet', DEFAULT_INVOICED_TIMESHEET)
        if param_invoiced_timesheet == 'approved':
            domain = expression.AND([domain, [('validated', '=', True)]])
        return domain
