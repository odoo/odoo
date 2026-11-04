from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_self_billing = fields.Boolean(
        string='Self Billing',
        help="This journal is for self-billing invoices. "
             "If the company has activated self-billing sending on Peppol, "
             "vendor bills will be available to be sent as self-billed invoices via Peppol.",
    )
