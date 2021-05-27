from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError



class AccountPaymentGroup(models.Model):
    _name = "account.payment.group"
    _description = "Payment Group"
    _order = "date desc"
    _inherit = 'mail.thread'
    _check_company_auto = True

    name = fields.Char(string='Number', required=True, readonly=True, copy=False, default='/')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True, change_default=True,
        default=lambda self: self.env.company, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        comodel_name='res.partner', string="Customer/Vendor", readonly=True, ondelete='restrict',
        states={'draft': [('readonly', False)]}, domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True)
    payment_ids = fields.One2many(
        'account.payment', 'payment_group_id', string='Payments', copy=False,
        readonly=True, states={'draft': [('readonly', False)]},)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], string='Status', required=True,
        readonly=True, copy=False, tracking=True, default='draft', index=True)
    date = fields.Date(
        string='Date', required=True, index=True, readonly=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Date.context_today)
    partner_type = fields.Selection(
        [('customer', 'Customer'), ('supplier', 'Vendor')], default='customer', tracking=True, required=True)
    unreconciled_amount = fields.Monetary(
        string='Adjustment / Advance', readonly=True, states={'draft': [('readonly', False)]})
    to_pay_move_line_ids = fields.Many2many(
        'account.move.line', string="To Pay Lines", help='This lines are the ones the user has selected to be paid.',
        copy=False, readonly=True, states={'draft': [('readonly', False)]}, check_company=True)
    # COMPUTED FIELDS
    to_pay_amount = fields.Monetary(
        compute='_compute_to_pay_amount', inverse='_inverse_to_pay_amount',
        string='To Pay Amount', readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    payments_amount = fields.Monetary(
        compute='_compute_payments_amount', string='Amount', tracking=True)
    payment_difference = fields.Monetary(
        compute='_compute_payment_difference', readonly=True, string="Payments Difference",
        help="Difference between selected debt (or to pay amount) and payments amount")
    selected_debt = fields.Monetary(string='Selected Debt', compute='_compute_selected_debt',)
    # TODO make currency editable
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True, tracking=True,
        default=lambda self: self.env.company.currency_id, readonly=True, states={'draft': [('readonly', False)]})

    @api.depends('to_pay_move_line_ids.amount_residual')
    def _compute_selected_debt(self):
        for rec in self:
            rec.selected_debt = sum(rec.to_pay_move_line_ids._origin.mapped('amount_residual')) * (-1.0 if rec.partner_type == 'supplier' else 1.0)

    @api.depends('selected_debt', 'unreconciled_amount')
    def _compute_to_pay_amount(self):
        for rec in self:
            rec.to_pay_amount = rec.selected_debt + rec.unreconciled_amount

    @api.depends('to_pay_amount', 'payments_amount')
    def _compute_payment_difference(self):
        for rec in self:
            rec.payment_difference = rec.to_pay_amount - rec.payments_amount

    @api.depends('payment_ids.amount_signed')
    def _compute_payments_amount(self):
        for rec in self:
            # TODO we should use amount_total_in_currency_signed or change the logic
            # the problem with amount_total_in_currency_signed is that is only computed after saving
            # rec.payments_amount = sum(rec.payment_ids.mapped('amount_total_in_currency_signed'))
            rec.payments_amount = sum(rec.payment_ids.mapped('amount_signed'))

    @api.onchange('to_pay_amount')
    def _inverse_to_pay_amount(self):
        for rec in self:
            rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt

    @api.onchange('partner_id', 'partner_type', 'company_id')
    def _refresh_payments_and_move_lines(self):
        if self._context.get('default_to_pay_move_line_ids'):
            return
        for rec in self:
            rec.add_all()

    def _get_to_pay_move_lines_domain(self):
        self.ensure_one()
        return [
            ('partner_id', '=', self.partner_id.id), ('company_id', '=', self.company_id.id), ('move_id.state', '=', 'posted'),
            ('account_id.reconcile', '=', True), ('reconciled', '=', False), ('full_reconcile_id', '=', False),
            ('account_id.internal_type', '=', 'receivable' if self.partner_type == 'customer' else 'payable'),
        ]

    def add_all(self):
        for rec in self:
            rec.to_pay_move_line_ids = rec.env['account.move.line'].search(rec._get_to_pay_move_lines_domain())

    def remove_all(self):
        self.to_pay_move_line_ids = False

    def action_cancel(self):
        self.mapped('payment_ids').action_cancel()
        self.write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.mapped('payment_ids').action_draft()
        return self.write({'state': 'draft'})

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_posted(self):
        recs = self.filtered(lambda x: x.state == 'posted')
        if recs:
            raise UserError(_('You can not delete posted payment groups. Payment group ids: %s') % recs.ids)

    def action_post(self):
        for rec in self.filtered(lambda x: not x.name or x.name == '/'):
            rec.name = self.env['ir.sequence'].next_by_code('account.payment.group.%s' % rec.partner_type)
        self.mapped('payment_ids').action_post()
        self.write({'state': 'posted'})
        return True

    @api.constrains('partner_id', 'to_pay_move_line_ids')
    def check_to_pay_lines(self):
        for rec in self:
            to_pay_partners = rec.to_pay_move_line_ids.mapped('partner_id')
            if len(to_pay_partners) > 1:
                raise ValidationError(_('All to pay lines must be of the same partner'))
            if len(rec.to_pay_move_line_ids.mapped('company_id')) > 1:
                raise ValidationError(_("You can't create payments for entries belonging to different companies."))
            if to_pay_partners and to_pay_partners != rec.partner_id:
                raise ValidationError(_('Payment group for partner %s but payment lines are of partner %s') % (
                    rec.partner_id.name, to_pay_partners.name))
