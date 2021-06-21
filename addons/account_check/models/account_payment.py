from odoo import fields, models, _, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_id = fields.Many2one('account.payment', string='Check', readonly=True, states={'draft': [('readonly', False)]}, copy=False,)
    available_check_ids = fields.Many2many('account.payment', compute='_compute_available_checks')
    amount = fields.Monetary(compute='_compute_amount', readonly=False, store=True)
    third_check_status = fields.Selection([
        ('draft', 'Draft'),
        ('holding', 'In Wallet'),
        ('deposited', 'Collected'),
        ('delivered', 'Delivered'),
        # ('withdrawed', 'Withdrawed'),
        # ('handed', 'Handed'),
        # ('debited', 'Debited'),
        # ('returned', 'Returned'),
    ],
        # required=True,
        # default='draft',
        copy=False,
        index=True,
    )
    third_check_issue_date = fields.Date(
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    third_check_bank_id = fields.Many2one(
        'res.bank',
        readonly=True,
        states={'draft': [('readonly', False)]},
        compute='_compute_third_check_data',
        store=True,
    )
    third_check_issuer_vat = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)]},
        store=True,
        compute='_compute_third_check_data',
    )
    third_check_issuer_name = fields.Char(
        readonly=True,
        states={'draft': [('readonly', False)]},
        compute='_compute_third_check_issuer_name',
        store=True,
    )

    @api.depends('check_id.amount')
    def _compute_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    @api.depends('payment_method_id.code', 'partner_id')
    def _compute_third_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_id.code == 'new_third_checks')
        (self - new_third_checks).update({'third_check_bank_id': False, 'third_check_issuer_vat': False, 'third_check_issue_date': False})
        for rec in new_third_checks:
            rec.update({
                'third_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'third_check_issuer_vat': rec.partner_id.vat,
                'third_check_issue_date': fields.Date.context_today(rec),
            })

    @api.depends('third_check_issuer_vat')
    def _compute_third_check_issuer_name(self):
        """ We suggest owner name from owner vat """
        with_vat = self.filtered(lambda x: x.third_check_issuer_vat)
        (self - with_vat).third_check_issuer_name = False
        for rec in with_vat:
            rec.third_check_issuer_name = self.search(
                [('third_check_issuer_vat', '=', self.third_check_issuer_vat)], limit=1).third_check_issuer_name or self.partner_id.name

    @api.depends('payment_method_id.code', 'partner_id', 'is_internal_transfer', 'journal_id')
    def _compute_available_checks(self):
        moved_third_checks = self.filtered(lambda x: x.payment_method_id.code in ['in_third_checks', 'out_third_checks'])
        (self - moved_third_checks).available_check_ids = self.env['account.payment']
        for rec in moved_third_checks:
            available_checks = rec.env['account.payment']
            operation, domain = rec._get_checks_operations()
            if domain:
                available_checks = available_checks.search(domain)
            rec.available_check_ids = available_checks

    @api.constrains('third_check_issue_date', 'check_payment_date')
    @api.onchange('third_check_issue_date', 'check_payment_date')
    def onchange_date(self):
        for rec in self:
            if rec.third_check_issue_date and rec.check_payment_date and rec.third_check_issue_date > rec.check_payment_date:
                raise UserError(_('Check Payment Date must be greater than Issue Date'))

    @api.constrains('payment_method_id', 'third_check_issuer_vat', 'third_check_bank_id', 'company_id', 'check_number')
    def _check_unique(self):
        for rec in self.filtered(lambda x: x.check_number and x.payment_method_id.code == 'new_third_checks'):
            same_checks = self.search([
                ('company_id', '=', rec.company_id.id),
                ('third_check_bank_id', '=', rec.third_check_bank_id.id),
                ('third_check_issuer_vat', '=', rec.third_check_issuer_vat),
                ('check_number', '=', rec.check_number),
            ])
            same_checks -= rec
            if same_checks:
                raise UserError(_(
                    'Check Number (%s) must be unique per Owner and Bank!'
                    '\n* Check ids: %s') % (rec.check_number, same_checks.ids))

    def _get_checks_operations(self):
        return self._get_checks_operations_model(self.payment_method_code, self.payment_type, self.is_internal_transfer, self.journal_id)

    @api.model
    def _get_checks_operations_model(self, payment_method_code, payment_type, is_internal_transfer, journal_id, destination_journal_id=None):
        """
        This method is called from:
        * cancellation of payment to execute delete the right operation and unlink check if needed
        * from post to add check operation and, if needded, change payment vals and/or create check and
        """
        domain = [('payment_method_code', '=', 'new_third_checks')]
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
        # elif payment_method_code == 'new_third_checks':
        #     return 'holding', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'draft')]
        elif payment_method_code == 'out_third_checks':
            return 'delivered', domain + [('journal_id', '=', journal_id.id), ('state', '=', 'holding')]
        elif payment_method_code == 'in_third_checks':
            return 'holding', domain + [('state', '=', 'delivered')]
        # raise UserError(_(
        #     'This operatios is not implemented for checks:\n'
        #     '* Payment type: %s\n'
        #     '* Payment method: %s\n%s') % (
        #         payment_type,
        #         payment_method_code,
        #         '* Destination journal: %s\n' % destination_journal_id.name if is_internal_transfer else ''))

    @api.onchange('available_check_ids')
    def reset_check_ids(self):
        self.check_id = False

    # @api.depends('payment_method_code')
    # def _compute_check_type(self):
    #     """ Method to """
    #     for rec in self:
    #         if rec.payment_method_code in ['new_third_checks', 'out_third_checks', 'in_third_checks']:
    #             rec.check_type = 'third_check'
    #         elif rec.payment_method_code in ['new_own_checks', 'in_own_checks']:
    #             rec.check_type = 'own_check'
    #         else:
    #             rec.check_type = False

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
