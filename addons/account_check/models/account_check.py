from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountCheck(models.Model):

    _name = 'account.check'
    _description = 'Account Check'
    _order = "id desc"
    _rec_name = 'number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    operation_ids = fields.One2many(
        'account.check.operation',
        'check_id',
        readonly=True,
    )
    name = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]},
        index=True,
    )
    number = fields.Integer(
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        compute='_compute_number',
        inverse='_inverse_number',
    )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        readonly=True,
        states={'draft': [('readonly', False)]},
        ondelete='restrict',
    )
    own_check_subtype = fields.Selection(
        related='checkbook_id.own_check_subtype',
    )
    type = fields.Selection(
        [('own_check', 'Own Check'), ('third_check', 'Third Check')],
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        # related is not working / updating as expected, we make computed
        compute='_compute_data',
        store=True,
        string='Last operation partner',
    )
    first_partner_id = fields.Many2one(
        'res.partner',
        string='First operation partner',
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('holding', 'In Wallet'),
        ('deposited', 'Collected'),
        ('delivered', 'Delivered'),
        ('withdrawed', 'Withdrawed'),
        ('handed', 'Handed'),
        ('debited', 'Debited'),
        ('returned', 'Returned'),
    ],
        required=True,
        default='draft',
        copy=False,
        compute='_compute_state',
        store=True,
        index=True,
    )
    issue_date = fields.Date(
        'Issue Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
    )
    issuer_vat = fields.Char(
        'Issuer Vat',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    issuer_name = fields.Char(
        'Issuer Name',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    bank_id = fields.Many2one(
        'res.bank', 'Bank',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    amount = fields.Monetary(
        currency_field='currency_id',
        readonly=True,
        required=True,
        states={'draft': [('readonly', False)]}
    )
    amount_company_currency = fields.Monetary(
        currency_field='company_currency_id',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )
    payment_date = fields.Date(
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        compute='_compute_data',
        readonly=True,
        required=True,
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company currency',
    )

    @api.depends('name')
    def _compute_number(self):
        for rec in self:
            rec.number = ''.join(filter(lambda x: x.isdigit(), rec.name or ''))

    @api.onchange('number')
    def _inverse_number(self):
        # TODO improve this, actually is harcoded to argentina the 8 digits number
        for rec in self:
            if rec.number:
                rec.name = '%08d' % rec.number

    @api.onchange('issuer_vat')
    def onchange_issuer_vat(self):
        """ We suggest owner name from owner vat """
        issuer_name = self.search([('issuer_vat', '=', self.issuer_vat)], limit=1).issuer_name
        if not issuer_name:
            issuer_name = self.first_partner_id.commercial_partner_id and self.first_partner_id.commercial_partner_id.name or False
        self.issuer_name = issuer_name

    @api.onchange('first_partner_id', 'type', 'journal_id')
    def onchange_type(self):
        if self.type == 'third_check':
            commercial_partner = self.first_partner_id.commercial_partner_id
            self.bank_id = commercial_partner.bank_ids and commercial_partner.bank_ids[0].bank_id or False
            self.issuer_vat = commercial_partner.vat
            self.checkbook_id = False
        else:
            self.bank_id = False
            self.issuer_name = False
            self.issuer_vat = False
            self.checkbook_id = self.env['account.checkbook'].search([('state', '=', 'active'), ('journal_id', '=', self.journal_id.id)], limit=1)

    @api.onchange('checkbook_id')
    def onchange_checkbook(self):
        if self.checkbook_id and not self.checkbook_id.numerate_on_printing:
            self.number = self.checkbook_id.next_number
            self._inverse_number()
        else:
            self.number = False

    @api.depends('operation_ids.move_line_id.partner_id', 'operation_ids.move_line_id.journal_id')
    def _compute_data(self):
        for rec in self.filtered('operation_ids'):
            move_line = rec.operation_ids.sorted()[0].move_line_id
            if move_line.partner_id:
                rec.partner_id = move_line.partner_id
            if move_line.journal_id:
                rec.journal_id = move_line.journal_id

    @api.constrains('issue_date', 'payment_date')
    @api.onchange('issue_date', 'payment_date')
    def onchange_date(self):
        for rec in self:
            if rec.issue_date and rec.payment_date and rec.issue_date > rec.payment_date:
                raise UserError(_('Check Payment Date must be greater than Issue Date'))

    @api.constrains('type', 'name',)
    def _own_number_interval(self):
        for rec in self:
            # if not range, then we dont check it
            if rec.type == 'own_check' and rec.checkbook_id.range_to and rec.number:
                if rec.number > rec.checkbook_id.range_to:
                    raise UserError(_(
                        "Check number (%s) can't be greater than %s on "
                        "checkbook %s (%s)") % (
                        rec.number,
                        rec.checkbook_id.range_to,
                        rec.checkbook_id.name,
                        rec.checkbook_id.id,
                    ))
                elif rec.number == rec.checkbook_id.range_to:
                    rec.checkbook_id.state = 'used'

    @api.constrains('type', 'issuer_name', 'bank_id')
    def _check_unique(self):
        for rec in self:
            if rec.type == 'own_check':
                same_checks = self.search([('checkbook_id', '=', rec.checkbook_id.id), ('type', '=', rec.type), ('name', '=', rec.name)])
                same_checks -= rec
                if same_checks:
                    raise ValidationError(_(
                        'Check Number (%s) must be unique per Checkbook!\n'
                        '* Check ids: %s') % (rec.name, same_checks.ids))
            elif rec.type == 'third_check':
                same_checks = self.search([
                    ('company_id', '=', rec.company_id.id),
                    ('bank_id', '=', rec.bank_id.id),
                    ('issuer_vat', '=', rec.issuer_vat),
                    ('type', '=', rec.type),
                    ('name', '=', rec.name),
                ])
                same_checks -= rec
                if same_checks:
                    raise ValidationError(_(
                        'Check Number (%s) must be unique per Owner and Bank!'
                        '\n* Check ids: %s') % (rec.name, same_checks.ids))

    def _del_operation(self, origin):
        """
        We check that the operation that is being cancel is the last operation
        done (same as check state)
        """
        for rec in self:
            if not rec.operation_ids or rec.operation_ids[0].move_line_id != origin:
                raise ValidationError(_(
                    'You can not cancel this operation because this is not '
                    'the last operation over the check.\nCheck (id): %s (%s)'
                ) % (rec.name, rec.id))
            rec.operation_ids[0].unlink()

    def _add_operation(self, operation, origin, date=False):
        for rec in self:
            rec._check_state_change(operation)
            # agregamos validacion de fechas
            date = date or fields.Datetime.now()
            if rec.operation_ids and rec.operation_ids[0].date > date:
                raise ValidationError(_(
                    'The date of a new check operation can not be minor than '
                    'last operation date.\n'
                    '* Check Id: %s\n'
                    '* Check Number: %s\n'
                    '* Operation: %s\n'
                    '* Operation Date: %s\n'
                    '* Last Operation Date: %s') % (
                    rec.id, rec.name, operation, date,
                    rec.operation_ids[0].date))
            vals = {
                'operation': operation,
                'date': date,
                'check_id': rec.id,
                'move_line_id': origin.id,
            }
            rec.operation_ids.create(vals)

    @api.depends(
        'operation_ids.operation',
        'operation_ids.date',
    )
    def _compute_state(self):
        for rec in self:
            if rec.operation_ids.sorted():
                operation = rec.operation_ids.sorted()[0].operation
                rec.state = operation
            else:
                rec.state = 'draft'

    def _check_state_change(self, operation):
        """
        We only check state change from _add_operation because we want to
        leave the user the possibility of making anything from interface.
        Necesitamos este chequeo para evitar, por ejemplo, que un cheque se
        agregue dos veces en un pago y luego al confirmar se entregue dos veces
        On operation_from_state_map dictionary:
        * key is 'to state'
        * value is 'from states'
        """
        self.ensure_one()
        old_state = self.state
        operation_from_state_map = {
            # 'draft': [False],
            'holding': ['draft', 'deposited', 'delivered', 'holding'],
            'delivered': ['holding'],
            'deposited': ['holding'],
            'handed': ['draft'],
            'withdrawed': ['draft'],
            'rejected': ['delivered', 'deposited', 'handed'],
            'debited': ['handed'],
            'returned': ['handed', 'holding'],
            # 'cancel': ['draft'],
        }
        from_states = operation_from_state_map.get(operation)
        if not from_states:
            raise ValidationError(_(
                'Operation %s not implemented for checks!') % operation)
        if old_state not in from_states:
            raise ValidationError(_(
                'You can not "%s" a check from state "%s"!\n'
                'Check nbr (id): %s (%s)') % (
                    self.operation_ids._fields['operation'].convert_to_export(
                        operation, self),
                    self._fields['state'].convert_to_export(old_state, self),
                    self.name,
                    self.id))

    @api.ondelete(at_uninstall=False)
    def check_unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise ValidationError(_(
                    'The Check must be in draft state for unlink !'))

    # TODO re enable
    # @api.constrains('currency_id', 'amount', 'amount_company_currency')
    # def _check_amounts(self):
    #     for rec in self.filtered(lambda x: not x.amount or not x.amount_company_currency):
    #         if rec.currency_id != rec.company_currency_id:
    #             raise ValidationError(_(
    #                 'If you create a check with different currency thant the '
    #                 'company currency, you must provide "Amount" and "Amount '
    #                 'Company Currency"'))
    #         elif not rec.amount:
    #             if not rec.amount_company_currency:
    #                 raise ValidationError(_('No puede crear un cheque sin importe'))
    #             rec.amount = rec.amount_company_currency
    #         elif not rec.amount_company_currency:
    #             rec.amount_company_currency = rec.amount

    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if rec.type == 'third_check':
                name = '%s (%s - %s)' % (name, rec.bank_id.name, rec.issuer_vat)
            result.append((rec.id, name))
        return result
