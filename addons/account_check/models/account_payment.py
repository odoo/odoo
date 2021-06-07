from odoo import fields, models, _, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_id = fields.Many2one('account.check', string='Check', readonly=True, states={'draft': [('readonly', False)]}, copy=False,)
    check_type = fields.Char(compute='_compute_check_type')
    available_check_ids = fields.Many2many('account.check', compute='_compute_check_data')
    amount = fields.Monetary(compute='_compute_amount', readonly=False, store=True)

    def _get_checks_operations(self):
        return self._get_checks_operations_model(self.payment_method_code, self.payment_type, self.is_internal_transfer, self.journal_id)

    @api.model
    def _get_checks_operations_model(self, payment_method_code, payment_type, is_internal_transfer, journal_id, destination_journal_id=None):
        """
        This method is called from:
        * cancellation of payment to execute delete the right operation and unlink check if needed
        * from post to add check operation and, if needded, change payment vals and/or create check and
        """
        if payment_method_code in ['new_third_checks', 'out_third_checks', 'in_third_checks']:
            # third checks
            domain = [('type', '=', 'third_check')]
            if is_internal_transfer:
                if payment_type == 'outbound':
                    if destination_journal_id and any(x.code == 'in_third_checks' for x in destination_journal_id.inbound_payment_method_ids):
                        # transferencia a otro diario de terceros
                        # TODO implementar el movimiento entre diarios de cheques de terceros con dos operations?
                        return (
                            'holding',
                            domain + [('journal_id', '=', journal_id.id), ('state', '=', 'holding')])
                    else:
                        # deposito o venta
                        return (
                            'deposited',
                            domain + [('journal_id', '=', journal_id.id), ('state', '=', 'holding')])
                elif payment_type == 'inbound':
                    # Deposit rejection
                    return (
                        'holding',
                        # we can get the rejected check in a diferent journal
                        # ('journal_id', '=', journal_id.id),
                        domain + [('state', '=', 'deposited')])
            elif payment_method_code == 'new_third_checks':
                return 'holding', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'draft')]
            elif payment_method_code == 'out_third_checks':
                return 'delivered', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'holding')]
            elif payment_method_code == 'in_third_checks':
                return 'holding', domain + [('state', '=', 'delivered')]
        elif payment_method_code in ['new_own_checks', 'in_own_checks']:
            # issue checks
            domain = [('type', '=', 'own_check')]
            if is_internal_transfer and payment_type == 'outbound':
                return 'withdrawed', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'draft')]
            elif payment_method_code == 'new_own_checks':
                return 'handed', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'draft')]
            elif payment_method_code == 'in_own_checks':
                return 'returned', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'handed'), ('partner_id.commercial_partner_id', '=', self.partner_id.commercial_partner_id.id)]
        raise UserError(_(
            'This operatios is not implemented for checks:\n'
            '* Payment type: %s\n'
            '* Payment method: %s\n%s') % (
                payment_type,
                payment_method_code,
                '* Destination journal: %s\n' % destination_journal_id.name if is_internal_transfer else ''))

    @api.onchange('available_check_ids')
    def reset_check_ids(self):
        self.check_id = False

    @api.depends('payment_method_code', 'partner_id', 'check_type', 'is_internal_transfer', 'journal_id')
    def _compute_check_data(self):
        for rec in self:
            available_checks = rec.env['account.check']
            if not rec.check_type:
                rec.available_check_ids = available_checks
                continue
            operation, domain = rec._get_checks_operations()
            if domain:
                available_checks = available_checks.search(domain)
            rec.available_check_ids = available_checks

    @api.depends('payment_method_code')
    def _compute_check_type(self):
        """ Method to """
        for rec in self:
            if rec.payment_method_code in ['new_third_checks', 'out_third_checks', 'in_third_checks']:
                rec.check_type = 'third_check'
            elif rec.payment_method_code in ['new_own_checks', 'in_own_checks']:
                rec.check_type = 'own_check'
            else:
                rec.check_type = False

    @api.depends('check_id.amount', 'check_type')
    def _compute_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    def action_post(self):
        """ this method is called when posting an account_move of a payment or the payment directly and do the
        check operations (handed, delivered, etc) """
        res = super(AccountPayment, self).action_post()
        for rec in self.filtered('check_id'):
            if not rec.currency_id.is_zero(rec.check_id.amount - rec.amount):
                raise UserError(_(
                    'El importe del pago no coincide con el importe del cheque seleccionado. Por favor intente '
                    'eliminar y volver a agregar el cheque.'))
            rec._do_checks_operations()
        return res

    def _do_checks_operations(self, cancel=False):
        operation, domain = self._get_checks_operations()
        if cancel:
            self.check_id._del_operation(self.move_id)
        else:
            self.check_id._add_operation(operation, self.move_id, date=self.date)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        if self.check_id:
            operation, domain = self._get_checks_operations()
            document_name = _('Check %s %s') % (self.check_id.name, operation)
            res[0].update({
                'name': self.env['account.move.line']._get_default_line_name(
                    document_name, self.amount, self.currency_id, self.date, partner=self.partner_id),
                'date_maturity': self.check_id.payment_date or self.date,
            })
        return res
