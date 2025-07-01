from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare


class L10nInWithholdWizard(models.TransientModel):
    _name = 'l10n_in.withhold.wizard'
    _description = "Withhold Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids', [])
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
        elif active_model == 'account.payment':
            if not active_record.partner_id:
                type_name = _("Vendor Payment") if active_record.partner_type == 'supplier' else _("Customer Payment")
                raise UserError(_("Please set a partner on the %s before creating a withhold.", type_name))
            result['related_payment_id'] = active_record.id
        return result

    reference = fields.Char(string="Reference")
    type_name = fields.Char(string="Type", compute='_compute_type_name')
    related_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice/Bill",
        readonly=True,
    )
    related_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Payment",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        compute='_compute_company_id'
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Currency",
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        compute='_compute_journal', precompute=True,
        readonly=False, store=True,
        required=True,
        check_company=True,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
    )
    l10n_in_tds_tax_type = fields.Char(
        string="Indian Tax Type",
        compute='_compute_l10n_in_tds_tax_type'
    )
    withhold_line_ids = fields.One2many(
        comodel_name='l10n_in.withhold.wizard.line',
        inverse_name='withhold_id',
        string="TDS Lines",
        readonly=False,
        store=True,
    )
    l10n_in_withholding_warning = fields.Json(string="Withholding warning", compute='_compute_l10n_in_withholding_warning')

    #  ===== Computes =====
    @api.depends('related_move_id', 'related_payment_id')
    def _compute_l10n_in_tds_tax_type(self):
        for wizard in self:
            withhold_type = wizard._get_withhold_type()
            l10n_in_tds_tax_type = False
            if withhold_type in ('in_withhold', 'in_refund_withhold'):
                l10n_in_tds_tax_type = 'purchase'
            elif withhold_type in ('out_withhold', 'out_refund_withhold'):
                l10n_in_tds_tax_type = 'sale'
            wizard.l10n_in_tds_tax_type = l10n_in_tds_tax_type

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_type_name(self):
        for wizard in self:
            if wizard.related_payment_id:
                wizard.type_name = _("Vendor Payment") if wizard.related_payment_id.partner_type == 'supplier' else _("Customer Payment")
            else:
                wizard.type_name = wizard.related_move_id.type_name

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.related_move_id.company_id or wizard.related_payment_id.company_id

    @api.depends('company_id')
    def _compute_journal(self):
        for wizard in self:
            wizard.journal_id = wizard.company_id.parent_ids.l10n_in_withholding_journal_id[-1:] or \
                                wizard.env['account.journal'].search([*self.env['account.journal']._check_company_domain(wizard.company_id), ('type', '=', 'general')], limit=1)

    @api.depends('related_payment_id', 'related_move_id', 'l10n_in_tds_tax_type', 'withhold_line_ids')
    def _compute_l10n_in_withholding_warning(self):
        for wizard in self:
            warnings = {}
            if wizard.l10n_in_tds_tax_type == 'purchase' and not wizard.related_move_id.commercial_partner_id.l10n_in_pan and any(
                    line.tax_id.amount != max(line.tax_id.l10n_in_section_id.l10n_in_section_tax_ids, key=lambda t: abs(t.amount)).amount
                    for line in wizard.withhold_line_ids
                ):
                warnings['lower_tds_tax'] = {
                    'message': _("As the Partner's PAN missing/invalid, it's advisable to apply TDS at the higher rate.")
                    }
            precision = self.currency_id.decimal_places
            if wizard.related_move_id and float_compare(wizard.related_move_id.amount_untaxed, sum(line.base for line in wizard.withhold_line_ids), precision_digits=precision) < 0:
                message = _("The base amount of TDS lines is greater than the amount of the %s", wizard.type_name)
                warnings['lower_move_amount'] = {
                    'message': message
                }
            wizard.l10n_in_withholding_warning = warnings

    def _get_withhold_type(self):
        if self.related_move_id:
            move_type = self.related_move_id.move_type
            withhold_type = {
                'out_invoice': 'out_withhold',
                'in_invoice': 'in_withhold',
                'out_refund': 'out_refund_withhold',
                'in_refund': 'in_refund_withhold',
            }[move_type]
        else:
            withhold_type = 'in_withhold' if self.related_payment_id.partner_type == 'supplier' else 'out_withhold'
        return withhold_type

    # ===== MOVE CREATION METHODS =====
    def action_create_and_post_withhold(self):
        self.ensure_one()
        withholding_account_id = self.company_id.l10n_in_withholding_account_id
        self._validate_withhold_data_on_post(withholding_account_id)

        # Withhold creation and posting
        vals = self._prepare_withhold_header()
        move_lines = self._prepare_withhold_move_lines(withholding_account_id)
        vals['line_ids'] = [Command.create(line) for line in move_lines]
        withhold = self.with_company(self.company_id).env['account.move'].create(vals)
        withhold.action_post()

        # If the withhold is created from a payment, there is no need to reconcile
        if not self.related_payment_id:
            wh_reconc = withhold.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
            inv_reconc = self.related_move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
            (inv_reconc + wh_reconc).reconcile()
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
        """ Prepare the header for the withhold entry """
        vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'partner_id': self.related_move_id.partner_id.id or self.related_payment_id.partner_id.id,
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

        partner = self.related_move_id.partner_id or self.related_payment_id.partner_id
        withhold_type = self._get_withhold_type()

        if withhold_type in ('in_withhold', 'in_refund_withhold'):
            partner_account = partner.property_account_payable_id
        else:
            partner_account = partner.property_account_receivable_id

        # Create move lines for each withhold line with the withholding tax and the base amount
        for line in self.withhold_line_ids:
            debit = line.base if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
            credit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else line.base
            vals.append(append_vals(1.0, line.base, debit, credit, withholding_account_id, [Command.set(line.tax_id.ids)]))
            total_amount += line.base
            total_tax += line.amount

        # Create move line for the sum of all withhold lines (total amount)
        debit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else total_amount
        credit = total_amount if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        vals.append(append_vals(1.0, total_amount, debit, credit, withholding_account_id, False))

        # Create move line for the sum of all withhold taxes (total tax)
        debit = total_tax if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        credit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else total_tax
        vals.append(append_vals(1.0, total_tax, debit, credit, partner_account, False))

        return vals

    def _validate_withhold_data_on_post(self, withholding_account_id):
        if not withholding_account_id:
            raise UserError(_("Please configure the withholding account from the settings"))
        if not self.withhold_line_ids:
            raise ValidationError(_("You must input at least one withhold line"))


class L10nInWithholdWizardLine(models.TransientModel):
    _name = 'l10n_in.withhold.wizard.line'
    _description = "Withhold Wizard Lines"

    base = fields.Monetary(string="Base")
    currency_id = fields.Many2one(related='withhold_id.currency_id')
    l10n_in_tds_tax_type = fields.Char(related='withhold_id.l10n_in_tds_tax_type')
    withhold_id = fields.Many2one(comodel_name='l10n_in.withhold.wizard', required=True)
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="TDS Tax",
        required=True,
    )
    amount = fields.Monetary(
        string="TDS Amount",
        compute='_compute_amount',
        store=True,
    )

    #  ===== Constraints =====
    @api.constrains('base', 'amount')
    def _check_amounts(self):
        for line in self:
            precision = line.currency_id.decimal_places
            if float_compare(line.amount, 0.0, precision_digits=precision) <= 0:
                raise ValidationError(_("Negative or zero values are not allowed in amount for withhold lines"))
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
