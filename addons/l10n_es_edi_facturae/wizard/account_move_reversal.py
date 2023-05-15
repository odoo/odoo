from odoo import models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_es_edi_facturae_reason_code = fields.Selection(
        selection=[
            ('01', 'Invoice number'),
            ('02', 'Invoice series'),
            ('03', 'Date of issue'),
            ('04', 'Name and surname/company name - Issuer'),
            ('05', 'Name and surname/company name - Recipient'),
            ('06', 'Tax identification Issuer/Oblige'),
            ('07', 'Tax identification Receiver'),
            ('08', 'Issuer/Oblige Address'),
            ('09', 'Receiving Address'),
            ('10', 'Transaction Details'),
            ('11', 'Tax rate to be applied'),
            ('12', 'Tax rate to be applied'),
            ('13', 'Date/Period to apply'),
            ('14', 'Invoice type'),
            ('15', 'Statutory letters'),
            ('16', 'Taxable amount'),
            ('80', 'Calculation of output quotas'),
            ('81', 'Calculation of withholding taxes'),
            ('82', 'Taxable amount modified by return of containers/packaging'),
            ('83', 'Taxable income modified by discounts and allowances'),
            ('84', 'Taxable income modified by final, judicial or administrative ruling'),
            ('85', 'Taxable income modified by unpaid tax assessments. Order of declaration of bankruptcy'),
        ], string='Spanish Facturae EDI Reason Code', default='10')

    def reverse_moves(self, is_modify=False):
        # Extends account_account
        res = super(AccountMoveReversal, self).reverse_moves(is_modify)
        self.new_move_ids.l10n_es_edi_facturae_reason_code = self.l10n_es_edi_facturae_reason_code
        return res
