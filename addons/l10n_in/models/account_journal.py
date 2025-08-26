from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_sale_journal_type = fields.Selection(
        selection=[
            ("tax_invoice", "Tax Invoice"),
            ("bill_of_supply", "Bill of Supply"),
            ("invoice_cum_bill_of_supply", "Invoice-cum-Bill of Supply"),
        ],
        string="Indian Sale Journal Type",
    )
