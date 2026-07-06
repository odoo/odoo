from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_do_purchase_type = fields.Selection(
        string="Purchase Type",
        help="Type of goods and services purchased, as expected on the DGII 606 report",
        selection=[
            ('1', "1 - Personnel Expenses"),
            ('2', "2 - Expenses for Work, Supplies and Services"),
            ('3', "3 - Rentals"),
            ('4', "4 - Fixed Asset Expenses"),
            ('5', "5 - Representation Expenses"),
            ('6', "6 - Other Admitted Deductions"),
            ('7', "7 - Financial Expenses"),
            ('8', "8 - Extraordinary Expenses"),
            ('9', "9 - Purchases and Expenses Part of the Cost of Sales"),
            ('10', "10 - Asset Acquisitions"),
            ('11', "11 - Insurance Expenses"),
        ],
        default='9',
    )
    l10n_do_payment_type = fields.Selection(
        string="Payment Type",
        help="Payment method, as expected on the DGII 606 report",
        selection=[
            ('1', "1 - Cash"),
            ('2', "2 - Check / Transfer / Deposit"),
            ('3', "3 - Credit / Debit Card"),
            ('4', "4 - Credit Purchase"),
            ('5', "5 - Barter"),
            ('6', "6 - Credit Notes"),
            ('7', "7 - Mixed"),
        ],
        default='2',
    )

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.country_code != 'DO' or not self.l10n_latam_use_documents:
            return domain
        if self.move_type == 'out_invoice' and not self.debit_origin_id:
            allowed_docs = [self.env.ref('l10n_do.ecf_31').id, self.env.ref('l10n_do.ecf_32').id] if self.partner_id.vat else [self.env.ref('l10n_do.ecf_32').id]
            domain.append(('id', 'in', allowed_docs))
        return domain

    def _l10n_do_get_ncf(self):
        """ NCF identifying the move on DGII reports: its fiscal document
        number, or its reference for moves without fiscal documents.
        Tolerates an empty recordset (e.g. the reversed entry of a move
        that is not a credit note), for which it returns ''.
        """
        if self.l10n_latam_use_documents:
            return self.l10n_latam_document_number or ''
        return self.ref or ''
