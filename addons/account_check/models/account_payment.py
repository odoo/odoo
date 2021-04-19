##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from itertools import zip_longest
import logging
# import odoo.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_ids = fields.Many2many(
        'account.check', string='Checks', copy=False,
        # TODO check if it can be improoved in odoo, we need this because if we make readonly=True the related fields
        # delivery_check_ids and issue_check_ids where not being writeable
        # readonly=True, states={'draft': [('readonly', False)]}
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]}
    )
    # TODO we should be able to remove this fields. Is only here because adding two times the same field with difrerent widget is not working
    delivery_check_ids = fields.Many2many(related='check_ids', string="Checks Delivered", readonly=False, states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]})
    # this fields is to help with code and view
    check_type = fields.Char(compute='_compute_check_type',)
    amount = fields.Monetary(compute='_compute_amount', readonly=False, store=True)
    available_check_ids = fields.Many2many('account.check', compute='_compute_available_checks')

    @api.depends('payment_method_code', 'partner_id')
    def _compute_available_checks(self):
        for rec in self:
            available_checks = rec.env['account.check']
            if rec.payment_method_code == 'delivered_third_check':
                available_checks = available_checks.search(
                    [('journal_id', '=', rec.journal_id.id), ('state', '=', 'holding'), ('type', '=', 'third_check')])
            elif rec.payment_method_code == 'returned_check':
                available_checks = available_checks.search(
                    [('journal_id', '=', rec.journal_id.id), ('state', '=', 'debited'), ('type', '=', 'issue_check'), ('partner_id', '=', rec.partner_id.id)])
            rec.available_check_ids = available_checks

    @api.depends('payment_method_code')
    def _compute_check_type(self):
        for rec in self:
            if rec.payment_method_code in ['issue_check', 'returned_check']:
                rec.check_type = 'issue_check'
            elif rec.payment_method_code in ['received_third_check', 'delivered_third_check']:
                rec.check_type = 'third_check'
            else:
                rec.check_type = False

    @api.depends('check_ids.amount', 'check_type', 'delivery_check_ids.amount')
    def _compute_amount(self):
        for rec in self.filtered('check_type'):
            # TODO when fixed and no needed anymore delivery_check_ids change here
            rec.amount = sum((rec.check_ids | rec.delivery_check_ids).mapped('amount'))
            # rec.amount = sum(rec.check_ids.mapped('amount'))

    # TODO agregar que si se cambia method se borren cheques?

    # TODO re enable this checks?
    # @api.constrains('check_ids')
    # def _check_checks(self):
    #     for rec in self:
    #         # we only overwrite if payment method is delivered
    #         if rec.payment_method_code == 'delivered_third_check':
    #             rec.amount = sum(rec.check_ids.mapped('amount'))
    #             currency = rec.check_ids.mapped('currency_id')

    #             if len(currency) > 1:
    #                 raise ValidationError(_(
    #                     'You are trying to deposit checks of difference'
    #                     ' currencies, this functionality is not supported'))
    #             elif len(currency) == 1:
    #                 rec.currency_id = currency.id

    #             # si es una entrega de cheques de terceros y es en otra moneda
    #             # a la de la cia, forzamos el importe en moneda de cia de los
    #             # cheques originales
    #             # escribimos force_amount_company_currency directamente en vez
    #             # de amount_company_currency por lo explicado en
    #             # _inverse_amount_company_currency
    #             if rec.currency_id != rec.company_currency_id:
    #                 rec.force_amount_company_currency = sum(
    #                     rec.check_ids.mapped('amount_company_currency'))

    def action_post(self):
        """ this method is called when posting an account_move of a payment or the payment directly and do two things:
        1. Do check operations (handed, delivered, etc)
        2. Split liquidity lines so that statements reconciliation and accounting analysis is suitable for checks management.
        When spliting the lines we also:
        a) modify name to be more representative
        b) add date_maturity from the check

        This split is done for now on this easy way but could be doable directly on draft states by modifying the way
        the lines are synchronized between move and payment.
        """
        res = super(AccountPayment, self).action_post()
        for rec in self.filtered('check_ids'):
            if not rec.currency_id.is_zero(sum(rec.check_ids.mapped('amount')) - rec.amount):
                raise UserError(_(
                    'La suma del pago no coincide con la suma de los cheques seleccionados. Por favor intente eliminar '
                    'y volver a agregar un cheque.'))
            # TODO check if needed
            # if rec.payment_method_code == 'issue_check' and (
            #         not rec.check_number or not rec.check_name):
            #     raise UserError(_(
            #         'Para mandar a proceso de firma debe definir número '
            #         'de cheque en cada línea de pago.\n'
            #         '* ID del pago: %s') % rec.id)
            operation = rec.do_checks_operations()
            liquidity_lines, counterpart_lines, writeoff_lines = rec._seek_for_lines()
            rec._split_aml_line_per_check(liquidity_lines, operation)

        return res

    def _split_aml_line_per_check(self, liquidity_lines, operation):
        """ Take an account move, find the move lines related to check and
        split them one per each check related to the payment
        """
        checks = self.check_ids

        liquidity_lines = liquidity_lines.with_context(check_move_validity=False)
        liquidity_line = liquidity_lines[0]
        amount_field = 'credit' if liquidity_line['credit'] else 'debit'
        new_name = _('Deposit check %s') if liquidity_line['credit'] else liquidity_line['name'] + _(' check %s')

        # if the move line has currency then we are delivering checks on a different currency than company one
        currency = liquidity_line['currency_id']
        currency_sign = amount_field == 'debit' and 1.0 or -1.0

        # with current implementation, liquidity_lines should only have only one line. This is because we're deleting
        # all other lines when reseting too draft because of the design of _synchronize_to_moves
        for check, liquidity_line in zip_longest(checks, liquidity_lines):
            new_name % check.name
            # payment_display_name['%s-%s' % (self.payment_type, self.partner_type)]
            # document, amount, currency, date, partner
            document_name = _('Check %s %s') % (check.name, operation)
            check_vals = {
                'name': liquidity_lines._get_default_line_name(
                    document_name, check.amount, self.currency_id, self.date, partner=self.partner_id),
                amount_field: check.amount_company_currency,
                'date_maturity': check.payment_date,
                'amount_currency': currency and currency_sign * check.amount,
            }
            if check and liquidity_line:
                liquidity_line.write(check_vals)
            elif check:
                check_vals = liquidity_lines[0].copy(default=check_vals)
            else:
                liquidity_line.unlink()
        self.move_id._check_balanced()
        return True

    # def _split_aml_line_per_check(self, lines_vals):
    #     """ Take an account mvoe, find the move lines related to check and
    #     split them one per earch check related to the payment
    #     """
    #     checks = self.check_ids

    #     liquidity_line = lines_vals[0]
    #     amount_field = 'credit' if liquidity_line['credit'] else 'debit'
    #     # new_name = _('Deposit check %s') if liquidity_line['credit'] else liquidity_line['name'] + _(' check %s')

    #     # if the move line has currency then we are delivering checks on a
    #     # different currency than company one
    #     currency = liquidity_line['currency_id']
    #     currency_sign = amount_field == 'debit' and 1.0 or -1.0
    #     liquidity_line.update({
    #         # 'name': new_name % checks[0].name,
    #         amount_field: checks[0].amount_company_currency,
    #         'date_maturity': checks[0].payment_date,
    #         'amount_currency': currency and currency_sign * checks[0].amount,
    #     })
    #     checks -= checks[0]
    #     for check in checks:
    #         check_vals = liquidity_line.copy()
    #         check_vals.update({
    #             # 'name': new_name % check.name,
    #             amount_field: check.amount_company_currency,
    #             'date_maturity': check.payment_date,
    #             'amount_currency': currency and currency_sign * check.amount,
    #         })
    #         lines_vals += [check_vals]
    #     return True

    # def _prepare_move_line_default_vals(self, write_off_line_vals=None):
    #     res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
    #     if self.check_type:
    #         self._split_aml_line_per_check(res)
    #     return res

    def do_checks_operations(self, cancel=False):
        """
        This method is called from:
        * cancellation of payment to execute delete the right operation and unlink check if needed
        * from post to add check operation and, if needded, change payment vals and/or create check and
        """
        self.ensure_one()
        # THIRD CHECKS OPERATIONS
        if self.payment_method_code == 'received_third_check' and self.payment_type == 'inbound':
            # receive third check
            if cancel:
                _logger.info('Cancel Receive Check')
                self.check_ids._del_operation(self)
                return None
            _logger.info('Receive Check')
            self.check_ids._add_operation('holding', self, self.partner_id, date=self.date)
            return _('received')
        elif self.payment_method_code == 'delivered_third_check' and self.is_internal_transfer:
            # deposit third check or move third checks to other thir checks journal
            # if destination journal is a third checks journal we are moving between third checks journals
            if any(x.code == 'received_third_check' for x in self.destination_journal_id.inbound_payment_method_ids):
                if cancel:
                    _logger.info('Cancel Transfer Check')
                    # TODO implementar, ahora tenemos que ver como juega con el pago destino
                    raise UserError('NOT IMPLEMENTED YET')
                    # self.check_ids._del_operation(self)
                    # self.check_ids._del_operation(self)
                    # receive_op = check._get_operation('holding')
                    # if receive_op.origin._name == 'account.payment':
                    #     check.journal_id = receive_op.origin.journal_id.id
                    # return None
                _logger.info('Transfer Check')
                self.check_ids._add_operation('transfered', self, False, date=self.date)
                self.check_ids._add_operation('holding', self.paired_internal_transfer_payment_id, False, date=self.date)
                self.check_ids.write({'journal_id': self.destination_journal_id.id})
                return _('transfered')
            else:
                # sell check
                if cancel:
                    _logger.info('Cancel Sell/Deposit Check')
                    self.check_ids._del_operation(self)
                    return None

                _logger.info('Sell/Deposit Check')
                self.check_ids._add_operation('selled' if self.destination_journal_id.type == 'cash' else 'deposited', self, self.partner_id, date=self.date)
                return _('selled') if self.destination_journal_id.type == 'cash' else _('deposited')
        elif self.payment_method_code == 'delivered_third_check':
            # deliver check
            if cancel:
                _logger.info('Cancel Deliver Check')
                self.check_ids._del_operation(self)
                return None
            _logger.info('Deliver Check')
            self.check_ids._add_operation('delivered', self, self.partner_id, date=self.date)
            return _('delivered')
        # ISSUE CHECKS OPERATIONS
        elif self.payment_method_code == 'issue_check' and not self.is_internal_transfer and self.payment_type == 'outbound':
            # issue checks
            if cancel:
                _logger.info('Cancel Issue Check')
                self.check_ids._del_operation(self)
                return None
            _logger.info('Issue Check')
            self.check_ids._add_operation('handed', self, self.partner_id, date=self.date)
            return _('issued')
        elif self.payment_method_code == 'issue_check' and self.is_internal_transfer and self.destination_journal_id.type == 'cash':
            # Take money from the bank with an own check
            if cancel:
                _logger.info('Cancel Withdrawal Check')
                self.check_ids._del_operation(self)
                return None
            _logger.info('Withdraw Check')
            self.check_ids._add_operation('withdrawed', self, self.partner_id, date=self.date)
            return _('withdrawed')
        elif self.check_ids:
            raise UserError(_(
                'This operatios is not implemented for checks:\n'
                '* Payment type: %s\n'
                '* Payment method: %s\n'
                '* Destination journal: %s\n') % (
                    self.payment_type,
                    self.payment_method_code,
                    self.destination_journal_id.type))

    # def _prepare_payment_moves(self):
    #     vals = super(AccountPayment, self)._prepare_payment_moves()

    #     force_account_id = self._context.get('force_account_id')
    #     all_moves_vals = []
    #     for rec in self:
    #         moves_vals = super(AccountPayment, rec)._prepare_payment_moves()

    #         # edit liquidity lines
    #         # Si se esta forzando importe en moneda de cia, usamos este importe para debito/credito
    #         vals = rec.do_checks_operations()
    #         if vals:
    #             moves_vals[0]['line_ids'][1][2].update(vals)

    #         # edit counterpart lines
    #         # use check payment date on debt entry also so that it can be used for NC/ND adjustaments
    #         if rec.check_type and rec.check_payment_date:
    #             moves_vals[0]['line_ids'][0][2]['date_maturity'] = rec.check_payment_date
    #         if force_account_id:
    #             moves_vals[0]['line_ids'][0][2]['account_id'] = force_account_id

    #         # split liquidity lines on detailed checks transfers
    #         if rec.payment_type == 'transfer' and rec.payment_method_code == 'delivered_third_check' \
    #            and rec.check_deposit_type == 'detailed':
    #             rec._split_aml_line_per_check(moves_vals[0]['line_ids'])
    #             rec._split_aml_line_per_check(moves_vals[1]['line_ids'])

    #         all_moves_vals += moves_vals

    #     return all_moves_vals

    # def do_print_checks(self):
    #     # si cambiamos nombre de check_report tener en cuenta en sipreco
    #     checkbook = self.mapped('checkbook_id')
    #     # si todos los cheques son de la misma chequera entonces buscamos
    #     # reporte específico para esa chequera
    #     report_name = len(checkbook) == 1 and  \
    #         checkbook.report_template.report_name \
    #         or 'check_report'
    #     check_report = self.env['ir.actions.report'].search(
    #         [('report_name', '=', report_name)], limit=1).report_action(self)
    #     # ya el buscar el reporte da el error solo
    #     # if not check_report:
    #     #     raise UserError(_(
    #     #       "There is no check report configured.\nMake sure to configure "
    #     #       "a check report named 'account_check_report'."))
    #     return check_report

    # def print_checks(self):
    #     if len(self.mapped('checkbook_id')) != 1:
    #         raise UserError(_(
    #             "In order to print multiple checks at once, they must belong "
    #             "to the same checkbook."))
    #     # por ahora preferimos no postearlos
    #     # self.filtered(lambda r: r.state == 'draft').post()

    #     # si numerar al imprimir entonces llamamos al wizard
    #     if self[0].checkbook_id.numerate_on_printing:
    #         if all([not x.check_name for x in self]):
    #             next_check_number = self[0].checkbook_id.next_number
    #             return {
    #                 'name': _('Print Pre-numbered Checks'),
    #                 'type': 'ir.actions.act_window',
    #                 'res_model': 'print.prenumbered.checks',
    #                 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'target': 'new',
    #                 'context': {
    #                     'payment_ids': self.ids,
    #                     'default_next_check_number': next_check_number,
    #                 }
    #             }
    #         # si ya están enumerados mandamos a imprimir directamente
    #         elif all([x.check_name for x in self]):
    #             return self.do_print_checks()
    #         else:
    #             raise UserError(_(
    #                 'Está queriendo imprimir y enumerar cheques que ya han '
    #                 'sido numerados. Seleccione solo cheques numerados o solo'
    #                 ' cheques sin número.'))
    #     else:
    #         return self.do_print_checks()
