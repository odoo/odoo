from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'
    # TODO ver esto, agregamos el id porque nos conviene mas que el orden por name
    _order = "date desc, id desc, name desc"

    check_id = fields.Many2one('account.payment', string='Check', readonly=True, states={'draft': [('readonly', False)]}, copy=False,)
    amount = fields.Monetary(compute='_compute_amount', store=True, recursive=True, copy=True,)
    third_check_last_journal_id = fields.Many2one('account.journal', compute='_compute_third_check_last_journal', store=True)
    third_check_operation_ids = fields.One2many('account.payment', 'check_id', readonly=True)
    third_check_from_state = fields.Char(compute='_compute_third_check_from_state')
    third_check_state = fields.Selection([
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
        readonly=True,
        copy=False,
        index=True,
    )
    third_check_issue_date = fields.Date(
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    third_check_bank_id = fields.Many2one(
        'res.bank',
        readonly=False,
        states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_third_check_data',
        store=True,
    )
    third_check_issuer_vat = fields.Char(
        readonly=False,
        states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_third_check_data',
        store=True,
    )
    third_check_issuer_name = fields.Char(
        readonly=False,
        states={'cancel': [('readonly', True)], 'posted': [('readonly', True)]},
        compute='_compute_third_check_issuer_name',
        store=True,
    )

    @api.depends('check_id.amount')
    def _compute_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    @api.depends('payment_method_line_id.code', 'partner_id')
    def _compute_third_check_data(self):
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        # (self - new_third_checks).update({'third_check_bank_id': False, 'third_check_issuer_vat': False, 'third_check_issue_date': False})
        for rec in new_third_checks:
            rec.update({
                'third_check_bank_id': rec.partner_id.bank_ids and rec.partner_id.bank_ids[0].bank_id or False,
                'third_check_issuer_vat': rec.partner_id.vat,
                'third_check_issue_date': fields.Date.context_today(rec),
            })

    @api.depends('third_check_issuer_vat', 'payment_method_line_id.code', 'partner_id')
    def _compute_third_check_issuer_name(self):
        """ We suggest owner name from owner vat """
        new_third_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        # (self - new_third_checks).third_check_issuer_name = False
        for rec in new_third_checks:
            rec.third_check_issuer_name = rec.third_check_issuer_vat and self.search(
                [('third_check_issuer_vat', '=', rec.third_check_issuer_vat)], limit=1).third_check_issuer_name or rec.partner_id.name

    @api.depends('payment_method_line_id.code', 'is_internal_transfer', 'destination_journal_id')
    def _compute_third_check_from_state(self):
        moved_third_checks = self.filtered(lambda x: x.payment_method_line_id.code in ['in_third_checks', 'out_third_checks'])
        (self - moved_third_checks).third_check_from_state = False
        for rec in moved_third_checks:
            from_state, to_state = rec._get_checks_states()
            rec.third_check_from_state = from_state

    @api.constrains('third_check_issue_date', 'check_payment_date')
    @api.onchange('third_check_issue_date', 'check_payment_date')
    def onchange_date(self):
        for rec in self:
            if rec.third_check_issue_date and rec.check_payment_date and rec.third_check_issue_date > rec.check_payment_date:
                raise UserError(_('Check Payment Date must be greater than Issue Date'))

    @api.constrains('payment_method_line_id', 'third_check_issuer_vat', 'third_check_bank_id', 'company_id', 'check_number')
    def _check_unique(self):
        for rec in self.filtered(lambda x: x.check_number and x.payment_method_line_id.code == 'new_third_checks'):
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

    def _get_checks_states(self):
        return self._get_checks_states_model(
            self.payment_method_code, self.payment_type, self.is_internal_transfer, self.destination_journal_id)

    @api.model
    def _get_checks_states_model(self, payment_method_code, payment_type, is_internal_transfer, destination_journal=None):
        """
        Regarding the payment data (transfer, inbound, outbound, payment mode, etc), this method returns a tuple with:
        * expected from state for a check
        * new state of the check after payment is posted
        """
        if is_internal_transfer:
            # if it's a transfer we don't know domain till destination journal is choosen
            if not destination_journal:
                return False, False
            if payment_type == 'outbound':
                if destination_journal and any(x.code == 'in_third_checks' for x in destination_journal.inbound_payment_method_line_ids):
                    # transferencia a otro diario de terceros
                    # TODO implementar el movimiento entre diarios de cheques de terceros con dos operations?
                    return 'holding', 'holding'
                else:
                    # deposito o venta
                    return 'holding', 'deposited'
            elif payment_type == 'inbound':
                if destination_journal and any(x.code == 'out_third_checks' for x in destination_journal.inbound_payment_method_line_ids):
                    # transferencia a otro diario de terceros
                    # TODO implementar el movimiento entre diarios de cheques de terceros con dos operations?
                    return 'holding', 'holding'
                else:
                    # Deposit rejection
                    return 'deposited', 'holding'
        elif payment_method_code == 'new_third_checks':
            return False, 'holding'
            # return 'holding', domain + [('third_check_last_journal_id', '=', journal.id), ('third_check_state', '=', 'draft')]
        elif payment_method_code == 'out_third_checks':
            return 'holding', 'delivered'
        elif payment_method_code == 'in_third_checks':
            return 'delivered', 'holding'

    @api.onchange('payment_method_line_id', 'is_internal_transfer', 'journal_id', 'destination_journal_id')
    def reset_check_ids(self):
        self.check_id = False

    @api.onchange('check_number')
    def _onchange_check_number(self):
        for rec in self.filtered(lambda x: x.journal_id.company_id.country_id.code == "AR"):
            try:
                if rec.check_number:
                    rec.check_number = '%08d' % int(rec.check_number)
            except Exception:
                pass

    @api.depends('third_check_operation_ids.journal_id', 'third_check_operation_ids.state', 'payment_method_line_id')
    def _compute_third_check_last_journal(self):
        new_checks = self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks')
        for rec in new_checks:
            third_check_operation = rec.third_check_operation_ids.filtered(lambda x: x.state == 'posted')
            if not third_check_operation:
                rec.third_check_last_journal_id = rec.journal_id
            else:
                rec.third_check_last_journal_id = third_check_operation.sorted()[0].journal_id

    def action_post(self):
        """ this method is called when posting an account_move of a payment or the payment directly and do the
        check operations (handed, delivered, etc) """
        res = super(AccountPayment, self).action_post()
        # for rec in self.filtered('check_id'):
        for rec in self.filtered(lambda x: x.payment_method_line_id.code == 'new_third_checks'):
            rec.check_id = rec.id
        # for rec in self.filtered('check_id'):
        #     if not rec.currency_id.is_zero(rec.check_id.amount - rec.amount):
        # for rec in self.filtered(lambda x: x.payment_method_line_id.code in ['new_third_checks', 'in_third_checks', 'out_third_checks']):
        # for rec in self.filtered(lambda x: x.payment_method_line_id.code in ['new_third_checks', 'in_third_checks', 'out_third_checks']):
        for rec in self.filtered('check_id'):
            # if rec.check_id and not rec.currency_id.is_zero(rec.check_id.amount - rec.amount):
            if not rec.currency_id.is_zero(rec.check_id.amount - rec.amount):
                raise UserError(_(
                    'El importe del pago no coincide con el importe del cheque seleccionado. Por favor intente '
                    'eliminar y volver a agregar el cheque.'))
            rec._add_third_check_operation()
        return res

    def _cancel_third_check_operation(self):
        """
        We check that the operation that is being cancel is the last operation
        done (same as check state)
        """
        self.ensure_one()
        check = self.check_id
        from_state, to_state = self._get_checks_states()
        operations = check.third_check_operation_ids.sorted()
        if operations and operations[0] != self:
            raise ValidationError(_(
                'You can not cancel this operation because this is not '
                'the last operation over the check.\nCheck (id): %s (%s)'
            ) % (check.check_number, check.id))
        msg = 'Check %s cancelled by %s' % (to_state, self)
        check.message_post(body=msg)
        check.third_check_state = from_state

    def _add_third_check_operation(self):
        self.ensure_one()
        # check = self if self.payment_method_line_id.code == 'new_third_checks' else self.check_id
        check = self.check_id
        from_state, to_state = self._get_checks_states()
        if from_state != check.third_check_state:
            raise ValidationError(_(
                "You can't set a check as '%s' from state '%s'!\n"
                "Check nbr (id): %s (%s)") % (
                    self._fields['third_check_state'].convert_to_export(to_state, self),
                    self._fields['third_check_state'].convert_to_export(check.third_check_state, self),
                    check.check_number,
                    check.id))

        # TODO re add check operation with new approach
        date = self.date or fields.Datetime.now()
        operations = check.third_check_operation_ids.sorted()
        if operations and operations[0].date > date:
            raise ValidationError(_(
                'The date of a new check operation can not be minor than '
                'last operation date.\n'
                '* Check Id: %s\n'
                '* Check Number: %s\n'
                '* Operation: %s\n'
                '* Operation Date: %s\n'
                '* Last Operation Date: %s') % (check.id, check.check_number, to_state, date, operations[0].date))

        msg = 'Check %s by %s' % (to_state, self)
        check.message_post(body=msg)
        check.third_check_state = to_state

    @api.model
    def _get_trigger_fields_to_sincronize(self):
        res = super()._get_trigger_fields_to_sincronize()
        return res + ('check_payment_date', 'check_number')

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check name and operation on liquidity line """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        check = self if self.payment_method_line_id.code == 'new_third_checks' else self.check_id
        if check:
            from_state, to_state = self._get_checks_states()
            document_name = _('Check %s %s') % (check.check_number, to_state)
            res[0].update({
                'name': self.env['account.move.line']._get_default_line_name(
                    document_name, self.amount, self.currency_id, self.date, partner=self.partner_id),
                'date_maturity': check.check_payment_date or self.date,
            })
        return res

    # @api.depends('move_id.name', 'payment_method_line_id', 'check_number')
    # def name_get(self):
    #     if self._context.get('show_check_number'):
    #         return [(payment.id, payment.check_number) for payment in self]
    #     return super().name_get()

    @api.depends_context('show_check_number')
    def name_get(self):
        """ We add check number to display_name for check_id m2o field """
        res_names = super().name_get()
        for i, (res_name, rec) in enumerate(zip(res_names, self)):
            if rec.check_number:
                res_names[i] = (res_name[0], "%s %s" % (res_name[1], _("(Check %s)" % rec.check_number)))
        return res_names

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """ Allow to search by check_number """
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('check_number', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def button_open_check_operations(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Check Operations"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'context': {'create': False},
            'domain': [('id', 'in', self.third_check_operation_ids.filtered(lambda x: x.state == 'posted').ids)],
        }
        return action

    def _create_paired_internal_transfer_payment(self):
        for rec in self.filtered(lambda x: x.payment_method_line_id.code in ['in_third_checks', 'out_third_checks']):
            destionation_payment_method_code = 'in_third_checks' if rec.payment_type == 'outbound' else 'out_third_checks'
            destination_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(lambda x: x.code == destionation_payment_method_code)
            if destination_payment_method:
                # If we're making a transfer between third checks journal, select third check method and journal on destination transfer
                super(AccountPayment, rec.with_context(
                    default_check_id=rec.check_id, default_payment_method_line_id=destination_payment_method.id))._create_paired_internal_transfer_payment()
            else:
                # if it's check move we add a reference on ref field for statements and also to make it more understandable
                super(AccountPayment, rec)._create_paired_internal_transfer_payment()
                rec.paired_internal_transfer_payment_id.ref = '%s%s' % (
                    rec.ref + ' - ' or '',
                    _('Check %s') % rec.check_id.check_number)
            self -= rec
        super(AccountPayment, self)._create_paired_internal_transfer_payment()
