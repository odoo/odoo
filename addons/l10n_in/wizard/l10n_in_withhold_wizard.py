from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare


class L10n_InWithholdWizard(models.TransientModel):
    _name = 'l10n_in.withhold.wizard'
    _description = "Withhold Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        if active_model not in ('account.move', 'account.payment') or not active_ids:
            raise UserError(_("TDS must be created from an Invoice or a Payment."))
        if len(active_ids) > 1:
            raise UserError(_("You can only create a withhold for only one record at a time."))
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
    tds_deduction = fields.Selection(
        selection=[
            ('normal', 'Normal Deduction'),
            ('lower', 'Lower Deduction'),
            ('higher', 'Higher Deduction'),
            ('no', 'No Deduction'),
        ],
        string="TDS Deduction",
        compute='_compute_tds_deduction',
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
    l10n_in_withholding_warning = fields.Json(string="Withholding warning", compute='_compute_l10n_in_withholding_warning')
    base = fields.Monetary(string="Base Amount", compute='_compute_base', store=True, readonly=False)
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="TDS Section",
        required=True,
        compute='_compute_tax_id',
        store=True,
        readonly=False,
    )
    amount = fields.Monetary(
        string="TDS Amount",
        compute='_compute_amount',
    )

    #  ===== Constraints =====
    @api.constrains('base')
    def _check_amounts(self):
        for wizard in self:
            if wizard.currency_id.compare_amounts(wizard.base, 0.0) <= 0:
                raise ValidationError(_("Negative or zero values are not allowed in Base Amount for withhold"))
            if wizard.currency_id.compare_amounts(wizard.amount, 0.0) <= 0:
                raise ValidationError(_("Negative or zero values are not allowed in TDS Amount for withhold"))

    #  ===== Computes =====
    @api.depends('related_move_id', 'related_payment_id')
    def _compute_l10n_in_tds_tax_type(self):
        for wizard in self:
            withhold_type = wizard._get_withhold_type()
            l10n_in_tds_tax_type = False
            if withhold_type in ('in_withhold', 'in_refund_withhold'):
                l10n_in_tds_tax_type = 'tds_purchase'
            elif withhold_type in ('out_withhold', 'out_refund_withhold'):
                l10n_in_tds_tax_type = 'tds_sale'
            wizard.l10n_in_tds_tax_type = l10n_in_tds_tax_type

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_tds_deduction(self):
        for wizard in self:
            related_partner = wizard.related_move_id.commercial_partner_id if wizard.related_move_id else wizard.related_payment_id.partner_id.commercial_partner_id
            wizard.tds_deduction = related_partner.l10n_in_pan_entity_id.tds_deduction if related_partner and related_partner.l10n_in_pan_entity_id else 'higher'

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

    @api.depends('related_payment_id', 'related_move_id', 'l10n_in_tds_tax_type', 'base', 'tax_id')
    def _compute_l10n_in_withholding_warning(self):
        for wizard in self:
            warnings = {}
            if wizard.tax_id and wizard.l10n_in_tds_tax_type == 'tds_purchase' and not wizard.related_move_id.commercial_partner_id.l10n_in_pan_entity_id \
                and wizard.tax_id.amount != max(wizard.tax_id.l10n_in_section_id.l10n_in_section_tax_ids, key=lambda t: abs(t.amount)).amount:
                warnings['lower_tds_tax'] = {
                    'message': _("As the Partner's PAN missing/invalid, it's advisable to apply TDS at the higher rate.")
                }
            precision = self.currency_id.decimal_places
            if wizard.related_move_id and float_compare(wizard.related_move_id.amount_untaxed, wizard.base, precision_digits=precision) < 0:
                message = _("The base amount of TDS is greater than the amount of the %s", wizard.type_name)
                warnings['lower_move_amount'] = {
                    'message': message
                }
            wizard.l10n_in_withholding_warning = warnings

    @api.depends('related_move_id', 'related_payment_id')
    def _compute_tax_id(self):
        for wizard in self:
            sections = wizard.related_move_id._get_l10n_in_tds_tcs_applicable_sections()
            if sections:
                accounts_by_section = {}
                for line in wizard.related_move_id.line_ids:
                    section = line.account_id.l10n_in_tds_tcs_section_id
                    if section in sections:
                        accounts_by_section[section] = line.account_id
                tax = self.env['account.tax']
                for section, account in accounts_by_section.items():
                    # Search for the last withhold move line that matches the pan entity and account and section
                    withhold_move_line = self.env['account.move.line'].search([
                        ('move_id.l10n_in_withholding_ref_move_id.commercial_partner_id.l10n_in_pan_entity_id', '=', wizard.related_move_id.commercial_partner_id.l10n_in_pan_entity_id.id),
                        ('move_id.l10n_in_withholding_ref_move_id.line_ids.account_id', 'in', account.id),
                        ('move_id.l10n_in_withholding_ref_move_id.line_ids.l10n_in_tds_tcs_section_id', 'in', section.id),
                        ('move_id.state', '=', 'posted'),
                        ('tax_ids.l10n_in_section_id', '=', section.id),
                    ], limit=1, order='id desc')
                    if withhold_move_line:
                        tax = withhold_move_line.tax_ids.filtered(lambda t: t.l10n_in_section_id == section)
                        break
                if tax:
                    wizard.tax_id = tax

    @api.depends('tax_id')
    def _compute_base(self):
        for wizard in self:
            if (
                wizard.tax_id and
                wizard.related_move_id and
                wizard.tax_id.l10n_in_section_id not in (self.env.ref('l10n_in.tds_section_194q'), self.env.ref('l10n_in.tds_section_194n'))
            ):
                sign = -1 if wizard.related_move_id.is_inbound() else 1
                wizard.base = sign * sum(wizard.related_move_id.line_ids.filtered(lambda l: l.account_id.l10n_in_tds_tcs_section_id == wizard.tax_id.l10n_in_section_id).mapped('balance'))

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        for wizard in self:
            tax_amount = 0.0
            if wizard.tax_id:
                taxes_res = wizard.tax_id.compute_all(
                    wizard.base,
                    currency=wizard.tax_id.company_id.currency_id,
                    quantity=1.0,
                    product=False,
                    partner=False,
                    is_refund=False,
                )
                tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            wizard.amount = abs(tax_amount)

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
        withhold._message_log(
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
            'l10n_in_withholding_ref_payment_id': self.related_payment_id.id
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

        partner = self.related_move_id.partner_id or self.related_payment_id.partner_id
        withhold_type = self._get_withhold_type()

        if withhold_type in ('in_withhold', 'in_refund_withhold'):
            partner_account = partner.property_account_payable_id
        else:
            partner_account = partner.property_account_receivable_id

        # Create move line for withholding tax and the base amount
        debit = self.base if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        credit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else self.base
        vals.append(append_vals(1.0, self.base, debit, credit, withholding_account_id, [Command.set(self.tax_id.ids)]))
        total_amount = self.base
        total_tax = self.amount

        # Create move line for the base amount
        debit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else total_amount
        credit = total_amount if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        vals.append(append_vals(1.0, total_amount, debit, credit, withholding_account_id, False))

        # Create move line for the tax amount
        debit = total_tax if withhold_type in ('in_withhold', 'out_refund_withhold') else 0.0
        credit = 0.0 if withhold_type in ('in_withhold', 'out_refund_withhold') else total_tax
        vals.append(append_vals(1.0, total_tax, debit, credit, partner_account, False))

        return vals

    def _validate_withhold_data_on_post(self, withholding_account_id):
        if not withholding_account_id:
            raise UserError(_("Please configure the withholding account from the settings"))
