# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.addons.l10n_id_efaktur_coretax.models.account_payment import GOV_TREASURER_OPT, EBUPOT_DOCUMENT_TYPE


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_id_ebupot_gov_treasurer_opt = fields.Selection(
        selection=GOV_TREASURER_OPT,
        string="Payment Option",
        help="Payment method (only used by government institution withholders/collectors)",
    )
    l10n_id_ebupot_sp2d_number = fields.Char(string="SP2D Number")
    l10n_id_ebupot_document_type = fields.Selection(
        selection=EBUPOT_DOCUMENT_TYPE,
        default='TaxInvoice',
        string="Document Type",
        help="Filled with the type of document that serves as the basis for withholding/collection",
    )
    l10n_id_ebupot_document_number = fields.Char(
        string="Document Number",
        compute='_compute_l10n_id_ebupot_document', store=True, readonly=False,
        help="Filled in with the number of the basic document for cutting/collection",
    )
    l10n_id_ebupot_document_date = fields.Date(
        string="Document Date",
        compute='_compute_l10n_id_ebupot_document', store=True, readonly=False,
        help="Filled with the date of the basic document for withholding/collection",
    )

    @api.depends('line_ids')
    def _compute_l10n_id_ebupot_document(self):
        """ Default the document number/date from the vendor bill being paid. """
        for wizard in self:
            bill = wizard.line_ids.move_id.filtered(lambda m: m.move_type in ('in_invoice', 'in_receipt'))[:1]
            wizard.l10n_id_ebupot_document_number = bill.ref
            wizard.l10n_id_ebupot_document_date = bill.invoice_date

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'withhold' in fields_list:
            if self.env.context.get('active_model') == 'account.move':
                moves = self.env['account.move'].browse(self.env.context.get('active_ids', []))
            elif self.env.context.get('active_model') == 'account.move.line':
                moves = self.env['account.move.line'].browse(self.env.context.get('active_ids', [])).move_id
            else:
                moves = self.env['account.move']

            # In Indonesia we must still report a 0% withholding tax (facility/exemption), but the framework
            # would drop its line by defaulting to "Payment Only". Default to "Withhold and Pay" to keep it.
            has_withholding = moves.line_ids.tax_ids.flatten_taxes_hierarchy().filtered('is_withholding_tax')
            if has_withholding and 'ID' in moves.company_id.mapped('account_fiscal_country_id.code'):
                res['withhold'] = 'withhold_pay'
        return res

    def _get_withholding_moves(self, batch):
        moves = super()._get_withholding_moves(batch)
        if self.company_id.account_fiscal_country_id.code != 'ID':
            return moves
        # A facility/exemption tax withholds nothing, but the vendor still needs an E-Bupot certificate for it,
        # so we keep any move that has a withholding tax even when it owes nothing.
        extra = batch['lines'].move_id.filtered(
            lambda m: m.is_invoice(include_receipts=True)
            and m.line_ids.tax_ids.flatten_taxes_hierarchy().filtered('is_withholding_tax')
        )
        return moves | extra

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals.update({
            'l10n_id_ebupot_gov_treasurer_opt': self.l10n_id_ebupot_gov_treasurer_opt,
            'l10n_id_ebupot_sp2d_number': self.l10n_id_ebupot_sp2d_number,
            'l10n_id_ebupot_document_type': self.l10n_id_ebupot_document_type,
            'l10n_id_ebupot_document_number': self.l10n_id_ebupot_document_number,
            'l10n_id_ebupot_document_date': self.l10n_id_ebupot_document_date,
        })
        return payment_vals
