from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_bg_customer_invoice = fields.Selection(string="Customer Invoices", selection='_l10n_bg_document_type_selection_values', default='01')
    l10n_bg_credit_notes = fields.Selection(string="Credit Notes", selection='_l10n_bg_document_type_selection_values', default='03')
    l10n_bg_debit_notes = fields.Selection(string="Debit Notes", selection='_l10n_bg_document_type_selection_values', default='02')

    def _l10n_bg_document_type_selection_values(self):
        return [
            ('01', '01 - Invoice'),
            ('02', '02 - Debit notice'),
            ('03', '03 - Credit notice'),
            ('07', '07 - Customs declaration'),
            ('09', '09 - Protocol or another document'),
            ('11', '11 - Invoice - cash account'),
            ('12', '12 - Debit notification - cash account'),
            ('13', '13 - Credit notification - cash account'),
            ('81', '81 - Report for the sales carried out'),
            ('82', '82 - Report for the sales carried out by a special levying procedure'),
            ('91', '91 - Protocol of due tax under Art. 151c, Para 3 of the Act'),
            ('93', '93 - Protocol of due tax under Art. 151c, Para 7 of the Act with a recipient being a person not applying the special regime'),
            ('94', '94 - Protocol of due tax under Art. 151c, Para 7 of the Act with a recipient being a person applying the special regime'),
        ]
