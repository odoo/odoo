from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare


class L10nInAccountWithhold(models.TransientModel):
    _name = 'l10n_in.account.withhold'
    _description = "Withhold Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        if len(active_ids) > 1:
            raise UserError(_("You can only create a withhold for only one record at a time."))
        if active_model not in ('account.move', 'account.payment') or not active_ids:
            raise UserError(_("TDS must be created from an Invoice or a Payment."))
        active_record = self.env[active_model].browse(active_ids)
        result['reference'] = _("TDS of %s", active_record.name)
        if active_model == 'account.move':
            if active_record.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') or active_record.state != 'posted':
                raise UserError(_("TDS must be created from Posted Customer Invoices, Customer Credit Notes, Vendor Bills or Vendor Refunds."))
            result['related_move_id'] = active_record.id
            result['type_name'] = active_record.type_name
            if active_record.move_type == 'in_invoice' and not active_record.partner_id.l10n_in_pan:
                result['display_null_pan_warning'] = True
        elif active_model == 'account.payment':
            display_map = active_record._get_aml_default_display_map()
            type_name = display_map.get((active_record.payment_type, active_record.partner_type))
            if not active_record.partner_id:
                raise UserError(_("Please set a partner on the %s before creating a withhold.", type_name))
            result['related_payment_id'] = active_record.id
            result['type_name'] = type_name
            if active_record.payment_type == 'outbound' and not active_record.partner_id.l10n_in_pan:
                result['display_null_pan_warning'] = True
        return result

    reference = fields.Char(string="Reference")
    type_name = fields.Char(string="Type")
    withhold_type = fields.Selection([
        ('in_withhold', "Purchase"),
        ('out_withhold', "Sale"),
        ('in_refund_withhold', "Purchase Refund"),
        ('out_refund_withhold', "Sale Refund"),
    ], string="Withholding Type", required=True, compute='_compute_withhold_type', store=True, precompute=True)
    related_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice/Bill",
        readonly=True,
    )
    move_amount_total = fields.Monetary(
        string="Amount Total",
        related='related_move_id.amount_total'
    )
    reconciled_withhold_amount = fields.Monetary(
        string="Reconciled TDS",
        compute='_compute_reconciled_withhold_amount',
    )
    related_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Payment",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        compute='_compute_partner_id'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        compute='_compute_company_id'
    )
    amount = fields.Monetary(
        string="Amount",
        compute='_compute_amount'
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        compute='_compute_journal',
        precompute=True,
        readonly=False,
        store=True,
        required=True,
        check_company=True,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Currency",
    )
    tds_group_id = fields.Many2one(
        comodel_name='account.tax.group',
        string="TDS Group",
        compute='_compute_tds_group_id',
    )
    type_tax_use = fields.Char(
        string="TDS Tax Type",
        compute='_compute_type_tax_use'
    )
    withhold_line_ids = fields.One2many(
        comodel_name='l10n_in.account.withhold.line',
        string="TDS Lines",
        inverse_name='withhold_id',
        readonly=False,
        store=True,
    )
    display_null_pan_warning = fields.Boolean(string="Display Null PAN warning")

    #  ===== Computes =====
    @api.depends('related_move_id')
    def _compute_reconciled_withhold_amount(self):
        for wizard in self:
            rc_amount = 0.0
            if wizard.related_move_id:
                reconciled_vals = wizard.related_move_id._get_all_reconciled_invoice_partials()
                rc_amount = sum(val['amount'] for val in reconciled_vals if val['aml'].move_id.l10n_in_withholding_ref_move_id)
            wizard.reconciled_withhold_amount = rc_amount

    @api.depends('company_id')
    def _compute_tds_group_id(self):
        for wizard in self:
            wizard.tds_group_id = self.env.ref(f'account.{wizard.company_id.id}_tds_group', raise_if_not_found=False)

    @api.depends('tds_group_id', 'withhold_type')
    def _compute_type_tax_use(self):
        for wizard in self:
            type_tax_use = False
            if wizard.withhold_type in ('in_withhold', 'in_refund_withhold'):
                type_tax_use = 'purchase'
            elif wizard.withhold_type in ('out_withhold', 'out_refund_withhold'):
                type_tax_use = 'sale'
            wizard.type_tax_use = type_tax_use

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_partner_id(self):
        for wizard in self:
            wizard.partner_id = wizard.related_move_id.partner_id or wizard.related_payment_id.partner_id

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.related_move_id.company_id or wizard.related_payment_id.company_id

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_amount(self):
        for wizard in self:
            wizard.amount = wizard.related_move_id.amount_untaxed or wizard.related_payment_id.amount

    @api.depends('company_id')
    def _compute_journal(self):
        for wizard in self:
            wizard.journal_id = wizard.company_id.l10n_in_withholding_journal_id or \
                                wizard.env['account.journal'].search([('company_id', '=', wizard.company_id.id), ('type', '=', 'general')], limit=1)

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_withhold_type(self):
        for wizard in self:
            if wizard.related_move_id:
                move_type = wizard.related_move_id.move_type
                wizard.withhold_type = {
                    'out_invoice': 'out_withhold',
                    'in_invoice': 'in_withhold',
                    'out_refund': 'out_refund_withhold',
                    'in_refund': 'in_refund_withhold',
                }[move_type]
            else:
                wizard.withhold_type = 'in_withhold' if wizard.related_payment_id.payment_type == 'outbound' else 'out_withhold'

    # ===== MOVE CREATION METHODS =====
    def action_create_and_post_withhold(self):
        self.ensure_one()
        withholding_account_id = self.company_id.l10n_in_withholding_account_id
        self._validate_withhold_data_on_post(withholding_account_id)

        # Withhold creation and posting
        vals = self._prepare_withhold_header()
        move_lines = self._prepare_withhold_move_lines(withholding_account_id)
        vals['line_ids'] = [Command.create(line) for line in move_lines]
        withhold = self.env['account.move'].create(vals)
        withhold.action_post()

        # If the withhold is created from a payment, there is no need to reconcile
        if not self.related_payment_id:
            wh_reconc = withhold.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
            inv_reconc = self.related_move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
            old_reconc = inv_reconc.matched_debit_ids.debit_move_id + inv_reconc.matched_credit_ids.credit_move_id
            old_tds_reconc = old_reconc.filtered(lambda l: l.move_id.l10n_in_is_withholding)
            to_unreconcile = old_reconc - old_tds_reconc

            # Unreconcile old entries excluding the tds lines and reconcile the new withhold entry
            to_unreconcile.remove_move_reconcile()
            (inv_reconc + wh_reconc).reconcile()
            (inv_reconc + to_unreconcile).reconcile()
        related_record = self.related_move_id or self.related_payment_id
        withhold.message_post(
            body=Markup("%s %s: <a href='#' data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
                _("TDS created from"),
                self.type_name,
                related_record._name,
                related_record.id,
                related_record.name
            ))
        return withhold

    def _prepare_withhold_header(self):
        """
        Prepare the header for the withhold entry
        """
        vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'move_type': 'entry',
            'ref': self.reference,
            'l10n_in_is_withholding': True,
            'l10n_in_withholding_ref_move_id': self.related_move_id.id or self.related_payment_id.move_id.id,
        }
        return vals

    def _prepare_withhold_move_lines(self, withholding_account_id):
        """
        Prepare the move lines for the withhold entry
        """
        def append_vals(quantity, price_unit, debit, credit, account_id, tax_ids):
            return {
                'quantity': quantity,
                'price_unit': price_unit,
                'debit': debit,
                'credit': credit,
                'account_id': account_id.id,
                'tax_ids': tax_ids,
            }

        vals = []
        total_amount = 0
        total_tax = 0

        related_move_id = self.related_move_id or self.related_payment_id.move_id

        if self.withhold_type in ('in_withhold', 'in_refund_withhold'):
            partner_account = related_move_id.partner_id.property_account_payable_id
        else:
            partner_account = related_move_id.partner_id.property_account_receivable_id

        # Create move lines for each withhold line with the withholding tax and the base amount
        for line in self.withhold_line_ids:
            debit = line.base if self.withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
            credit = 0.0 if self.withhold_type in ('in_withhold', 'out_refund_withhold') else line.base
            vals.append(append_vals(1.0, line.base, debit, credit, withholding_account_id, [Command.set(line.tax_id.ids)]))
            total_amount += line.base
            total_tax += line.amount

        # Create move line for the sum of all withhold lines (total amount)
        debit = 0.0 if self.withhold_type in ('in_withhold', 'out_refund_withhold') else total_amount
        credit = total_amount if self.withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        vals.append(append_vals(1.0, total_amount, debit, credit, withholding_account_id, False))

        # Create move line for the sum of all withhold taxes (total tax)
        debit = total_tax if self.withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        credit = 0.0 if self.withhold_type in ('in_withhold', 'out_refund_withhold') else total_tax
        vals.append(append_vals(1.0, total_tax, debit, credit, partner_account, False))

        return vals

    def _validate_withhold_data_on_post(self, withholding_account_id):
        if not withholding_account_id:
            raise UserError(_("Please configure withholding account from settings"))
        if not self.withhold_line_ids:
            raise ValidationError(_("You must input at least one withhold line"))
        if self.related_move_id and sum(line.base for line in self.withhold_line_ids) > self.amount:
            raise ValidationError(_(
                "The total base amount can not exceed %(type_name)s %(amount_type)s",
                type_name=self.type_name,
                amount_type="Untaxed Amount" if self.related_move_id else "Amount",
            ))


class L10nInAccountWithholdLine(models.TransientModel):
    _name = 'l10n_in.account.withhold.line'
    _description = "Withhold Wizard Lines"

    base = fields.Monetary(string="Base")
    company_id = fields.Many2one(related='withhold_id.company_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    tds_group_id = fields.Many2one(related='withhold_id.tds_group_id')
    type_tax_use = fields.Char(related='withhold_id.type_tax_use')
    sequence = fields.Integer(default=10)
    withhold_id = fields.Many2one(comodel_name='l10n_in.account.withhold', required=True)
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="TDS Tax",
        required=True,
    )
    amount = fields.Monetary(
        string="TDS Amount",
        compute='_compute_amount',
        store=True,
        readonly=False
    )

    #  ===== Constraints =====
    @api.constrains('base', 'amount')
    def _check_amounts(self):
        for line in self:
            precision = line.currency_id.decimal_places
            if float_compare(line.amount, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_("Negative values are not allowed in amount for withhold lines"))
            if float_compare(line.base, 0.0, precision_digits=precision) <= 0:
                raise ValidationError(_("Negative or zero values are not allowed in base for withhold lines"))

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for line in self:
            tax_amount = 0.0
            if line.tax_id:
                tax_amount = line._tax_compute_all_helper(line.base, line.tax_id)
            line.amount = tax_amount

    # === Helper methods ====
    @api.model
    def _tax_compute_all_helper(self, base, tax_id):
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = tax_id.compute_all(
            base,
            currency=tax_id.company_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
        tax_amount = abs(tax_amount)
        return tax_amount
