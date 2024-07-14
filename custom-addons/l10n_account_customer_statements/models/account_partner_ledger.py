# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    @api.model
    def action_print_customer_statements(self, options, params):
        """ Print the customer statements for a specific customer.
        It is not directly based on the report lines, as we may print it outside the report too.
        """
        model, record_id = self.env['account.report']._get_model_info_from_id(params['line_id'])
        if model != 'res.partner':
            raise UserError(_("This option is only available for customers."))
        return self.env[model].browse(record_id).action_print_customer_statements(options)
