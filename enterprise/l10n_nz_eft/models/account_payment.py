# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------
    # Fields declaration
    # ------------------

    # Payer
    l10n_nz_payer_particulars = fields.Char(
        string='Payer Particulars',
        help='Particulars to write down on the payment in the bank account.'
    )
    l10n_nz_payer_code = fields.Char(
        string='Payer Analysis Code',
        help='Analysis code to use for the payment in the bank account.'
    )
    l10n_nz_available_dd_bank_ids = fields.Many2many(
        comodel_name='res.partner.bank',
        compute='_compute_l10n_nz_available_dd_bank_ids',
    )
    # As we are not using mandates, we need a way to provide this account when using direct debit.
    l10n_nz_dd_account_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Bank Account",
        readonly=False,
        store=True,
        tracking=True,
        compute='_compute_l10n_nz_dd_account_id',
        domain="[('id', 'in', l10n_nz_available_dd_bank_ids)]",
        check_company=True,
        ondelete='restrict',
    )

    # Payee
    l10n_nz_payee_particulars = fields.Char(
        string='Payee Particulars',
        help='Particulars to write down on the payment in the bank account.'
    )
    l10n_nz_payee_code = fields.Char(
        string='Payee Analysis Code',
        help='Analysis code to use for the payment in the bank account.'
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('partner_id', 'company_id', 'payment_type')
    def _compute_l10n_nz_available_dd_bank_ids(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.l10n_nz_available_dd_bank_ids = pay.partner_id.bank_ids.filtered(lambda x: x.company_id.id in (False, pay.company_id.id))._origin
            else:
                pay.l10n_nz_available_dd_bank_ids = False

    @api.depends('l10n_nz_available_dd_bank_ids')
    def _compute_l10n_nz_dd_account_id(self):
        """ The default partner_bank_id will be the first available on the partner. """
        for pay in self:
            pay.l10n_nz_dd_account_id = pay.l10n_nz_available_dd_bank_ids[:1]._origin

    # ----------------
    # Business methods
    # ----------------

    @api.model
    def _get_method_codes_using_bank_account(self):
        # EXTENDS account
        res = super()._get_method_codes_using_bank_account()
        res.extend(['l10n_nz_eft_in', 'l10n_nz_eft_out'])
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        # EXTENDS account
        res = super()._get_method_codes_needing_bank_account()
        res.extend(['l10n_nz_eft_in', 'l10n_nz_eft_out'])
        return res

    def action_post(self):
        # EXTENDS account
        # Do not allow to post if the account is required but not trusted
        for payment in self:
            if payment.payment_method_code == 'l10n_nz_eft_in' and not payment.l10n_nz_dd_account_id.allow_out_payment:
                raise UserError(_('To record payments with %s, the Payer Bank Account must be manually validated. '
                                  'You should go on the bank account in order to validate it.', self.payment_method_line_id.name))

        super().action_post()
