# pylint: disable=protected-access
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import index_exists, drop_index


_logger = logging.getLogger(__name__)


class l10nLatamAccountPaymentCheck(models.Model):
    _name = 'l10n_latam.account.payment.check'
    _description = 'Account payment check'
    _check_company_auto = True

    payment_id = fields.Many2one(
        'account.payment',
        required=True,
        ondelete='cascade',
        delegate=True,
    )
    payment_method_line_id = fields.Many2one(related='payment_id.payment_method_line_id', store=True)
    l10n_latam_check_operation_ids = fields.Many2many(
        comodel_name='account.payment',
        relation='account_payment_account_payment_check_rel',
        column1="check_id",
        column2="payment_id",
        required=True,
        string='Check Operations',
        readonly=True,
    )
    l10n_latam_check_current_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Check Current Journal",
        compute='_compute_check_info', store=True,
    )
    company_id = fields.Many2one(related='payment_id.company_id')
    currency_id = fields.Many2one(related='payment_id.currency_id')
    name = fields.Char(string='Number')
    l10n_latam_check_bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Check Bank',
        compute='_compute_l10n_latam_check_bank_id', store=True, readonly=False,
    )
    l10n_latam_check_issuer_vat = fields.Char(
        string='Check Issuer VAT',
        # compute='_compute_l10n_latam_check_issuer_vat', store=True, readonly=False,
    )
    l10n_latam_check_payment_date = fields.Date(
        string='Check Cash-In Date',
        help="Date from when you can cash in the check, turn the check into cash",
        readonly=False,
    )
    amount = fields.Monetary()
    split_move_line_id = fields.Many2one('account.move.line')
    reconcile_move_line_id = fields.Many2one('account.move.line')
    issue_state = fields.Selection([('handed', 'Handed'), ('debited', 'Debited'), ('voided', 'Voided')],
                                   compute='_compute_issue_state', store=True)

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'l10n_latam_account_payment_check_unique'):
            # issue_state is used to know that is an own check and also that is posted
            self.env.cr.execute("""
                CREATE UNIQUE INDEX l10n_latam_account_payment_check_unique
                    ON l10n_latam_account_payment_check(name, payment_method_line_id)
                WHERE issue_state is not null
            """)

    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            self.name = self.name.zfill(8)

    def _prepare_void_move_vals(self):
        return {
                'ref': 'Void check',
                'journal_id': self.split_move_line_id.move_id.journal_id.id,
                'line_ids': [Command.create({
                    'name': "Void check %s" % self.split_move_line_id.name,
                    'date_maturity': self.split_move_line_id.date_maturity,
                    'amount_currency': self.split_move_line_id.amount_currency,
                    'currency_id': self.split_move_line_id.currency_id.id,
                    'debit': self.split_move_line_id.debit,
                    'credit': self.split_move_line_id.credit,
                    'partner_id': self.split_move_line_id.partner_id.id,
                    'account_id': self.payment_id.destination_account_id.id,
                   }),
                    Command.create({
                        'name': "Void check %s" % self.split_move_line_id.name,
                        'date_maturity': self.split_move_line_id.date_maturity,
                        'amount_currency': -self.split_move_line_id.amount_currency,
                        'currency_id': self.split_move_line_id.currency_id.id,
                        'debit': -self.split_move_line_id.debit,
                        'credit': -self.split_move_line_id.credit,
                        'partner_id': self.split_move_line_id.partner_id.id,
                        'account_id': self.split_move_line_id.account_id.id,
                     })]
            }

    @api.depends('split_move_line_id.amount_residual')
    def _compute_issue_state(self):
        for rec in self:
            if not rec.split_move_line_id:
                rec.issue_state = False
            elif rec.amount and not rec.split_move_line_id.amount_residual:
                reconciled_line = rec.split_move_line_id.full_reconcile_id.reconciled_line_ids - rec.split_move_line_id
                voides_types = ['liability_payable', 'assets_receivable']
                if (reconciled_line.move_id.line_ids - reconciled_line).mapped('account_id.account_type')[0] in voides_types:
                    rec.issue_state = 'voided'
                else:
                    rec.issue_state = 'debited'
            else:
                rec.issue_state = 'handed'

    def action_void(self):
        for rec in self.filtered('split_move_line_id'):
            void_move = rec.env['account.move'].create(rec._prepare_void_move_vals())
            void_move.action_post()
            (void_move.line_ids[1] + rec.split_move_line_id).reconcile()

    @api.depends('state', 'l10n_latam_check_operation_ids.state')
    def _compute_check_info(self):
        for rec in self:
            last_operation = (rec.payment_id + rec.l10n_latam_check_operation_ids).filtered(
                lambda x: x.state == 'posted').sorted(key=lambda payment: (payment.date, payment.id))[-1:]
            if not last_operation:
                rec.l10n_latam_check_current_journal_id = False
                continue
            if last_operation.is_internal_transfer and last_operation.payment_type == 'outbound':
                rec.l10n_latam_check_current_journal_id = last_operation.paired_internal_transfer_payment_id.journal_id
            elif last_operation.payment_type == 'inbound':
                rec.l10n_latam_check_current_journal_id = last_operation.journal_id
            else:
                rec.l10n_latam_check_current_journal_id = False

    def button_open_check_operations(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        operations = ((self.l10n_latam_check_operation_ids + self.payment_id).filtered(lambda x: x.state == 'posted'))
        action = {
            'name': _("Check Operations"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': [
                (self.env.ref('l10n_latam_check.view_account_third_party_check_operations_tree').id, 'tree'),
                (False, 'form')],
            'context': {'create': False},
            'domain': [('id', 'in', operations.ids)],
        }
        return action

    def action_show_reconciled_move(self):
        self.ensure_one()
        move_id = self._get_reconciled_move()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': move_id.id,
        }

    def action_show_split_move(self):
        self.ensure_one()
        move_id = self.split_move_line_id.move_id
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': move_id.id,
        }

    def _get_reconciled_move(self):
        reconciled_line = self.split_move_line_id.full_reconcile_id.reconciled_line_ids - self.split_move_line_id
        return (reconciled_line.move_id.line_ids - reconciled_line).mapped('move_id')

    @api.constrains('amount')
    def _constrains_min_amount(self):
        min_amount_error = self.filtered(lambda x: x.amount <= 0)
        if min_amount_error:
            raise ValidationError(_('The amount of the check must be greater than 0'))

    # @api.depends('payment_register_id.payment_method_line_id.code', 'payment_register_id.partner_id')
    # def _compute_l10n_latam_check_bank_id(self):
    #     new_third_party_checks = self.filtered(lambda x: x.payment_register_id.payment_method_line_id.code == 'new_third_party_checks')
    #     for rec in new_third_party_checks:
    #         rec.l10n_latam_check_bank_id = rec.payment_register_id.partner_id.bank_ids[:1].bank_id
    #     (self - new_third_party_checks).l10n_latam_check_bank_id = False

    # @api.depends('payment_register_id.payment_method_line_id.code', 'payment_register_id.partner_id')
    # def _compute_l10n_latam_check_issuer_vat(self):
    #     new_third_party_checks = self.filtered(lambda x: x.payment_register_id.payment_method_line_id.code == 'new_third_party_checks')
    #     for rec in new_third_party_checks:
    #         rec.l10n_latam_check_issuer_vat = rec.payment_register_id.partner_id.vat
    #     (self - new_third_party_checks).l10n_latam_check_issuer_vat = False


    # @api.onchange('l10n_latam_check_issuer_vat')
    # def _clean_l10n_latam_check_issuer_vat(self):
    #     for rec in self.filtered(lambda x: x.l10n_latam_check_issuer_vat and x.company_id.country_id.code):
    #         stdnum_vat = stdnum.util.get_cc_module(rec.company_id.country_id.code, 'vat')
    #         if hasattr(stdnum_vat, 'compact'):
    #             rec.l10n_latam_check_issuer_vat = stdnum_vat.compact(rec.l10n_latam_check_issuer_vat)

    # @api.constrains('l10n_latam_check_issuer_vat', 'company_id')
    # def _check_l10n_latam_check_issuer_vat(self):
    #     for rec in self.filtered(lambda x: x.l10n_latam_check_issuer_vat and x.company_id.country_id):
    #         if not self.env['res.partner']._run_vat_test(rec.l10n_latam_check_issuer_vat, rec.company_id.country_id):
    #             error_message = self.env['res.partner']._build_vat_error_message(
    #                 rec.company_id.country_id.code.lower(), rec.l10n_latam_check_issuer_vat, 'Check Issuer VAT')
    #             raise ValidationError(error_message)
