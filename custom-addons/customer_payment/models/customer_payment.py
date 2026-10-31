from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CustomerPayment(models.Model):
    _name = 'customer.payment'
    _description = 'Customer Payment Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain=[('customer_rank', '>', 0)], tracking=True)
    year = fields.Integer(string='Year', required=True, default=lambda self: fields.Date.today().year, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Invoice related fields
    invoice_ids = fields.Many2many('account.move', 'customer_payment_invoice_rel',
                                    'payment_id', 'invoice_id',
                                    string='Invoices', readonly=True)
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_totals', store=True)
    total_invoice_amount = fields.Monetary(string='Total Invoices', compute='_compute_invoice_totals',
                                           store=True, currency_field='currency_id')

    # Payment entry related fields
    payment_entry_ids = fields.One2many('payment.entry', 'payment_id', string='Payment Entries')
    previous_payment_entry_ids = fields.Many2many('payment.entry', string='Previous Payment Entries',
                                                   compute='_compute_previous_payment_entries',
                                                   help='Payment entries from previous customer payment records')
    payment_entry_count = fields.Integer(string='Payment Entry Count', compute='_compute_payment_totals', store=True)
    total_payment_amount = fields.Monetary(string='Total Payments', compute='_compute_payment_totals',
                                           store=True, currency_field='currency_id')

    # Balance
    balance = fields.Monetary(string='Balance', compute='_compute_balance',
                              store=True, currency_field='currency_id',
                              help='Total Invoices - Total Payments')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('customer.payment') or 'New'
        return super(CustomerPayment, self).create(vals_list)

    @api.depends('partner_id', 'year')
    def _compute_previous_payment_entries(self):
        for record in self:
            if record.partner_id:
                # Find all payment entries from OTHER customer.payment records for this partner
                previous_payments = self.env['customer.payment'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('id', '!=', record.id),  # Exclude current record
                ])
                record.previous_payment_entry_ids = previous_payments.mapped('payment_entry_ids')
            else:
                record.previous_payment_entry_ids = False

    @api.depends('invoice_ids', 'invoice_ids.amount_total')
    def _compute_invoice_totals(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
            record.total_invoice_amount = sum(record.invoice_ids.mapped('amount_total'))

    @api.depends('payment_entry_ids', 'payment_entry_ids.amount', 'partner_id')
    def _compute_payment_totals(self):
        for record in self:
            # Get previous payment entries manually
            if record.partner_id:
                previous_payments = self.env['customer.payment'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('id', '!=', record.id),
                ])
                previous_entries = previous_payments.mapped('payment_entry_ids')
            else:
                previous_entries = self.env['payment.entry']

            # Count and sum both previous and new payment entries
            all_entries = previous_entries + record.payment_entry_ids
            record.payment_entry_count = len(all_entries)
            record.total_payment_amount = sum(all_entries.mapped('amount'))

    @api.depends('total_invoice_amount', 'total_payment_amount')
    def _compute_balance(self):
        for record in self:
            record.balance = record.total_invoice_amount - record.total_payment_amount

    def action_process_invoices(self):
        """Process button to fetch all invoices for the selected customer and year"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        if not self.year:
            raise UserError(_('Please specify a year.'))

        # Find all invoices for this customer in the specified year
        date_start = fields.Date.from_string(f'{self.year}-01-01')
        date_end = fields.Date.from_string(f'{self.year}-12-31')

        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_start),
            ('invoice_date', '<=', date_end),
        ])

        self.write({
            'invoice_ids': [(6, 0, invoices.ids)],
            'state': 'processed',
        })

        # Send notification to user
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'web.notify',
            {
                'type': 'success',
                'title': _('Success'),
                'message': _('%s invoices loaded for %s in year %s') % (
                    len(invoices), self.partner_id.name, self.year
                ),
                'sticky': False,
            }
        )

        # Return True to let the framework refresh the view
        return True

    def action_reset_to_draft(self):
        """Reset to draft and clear invoices"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'invoice_ids': [(5, 0, 0)],
        })
