from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare


class L10nAccountWithholdWizard(models.TransientModel):
    _name = 'l10n.account.withhold.wizard'
    _description = "Withhold Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model != 'account.move':
            raise UserError(_("You can only create a withhold for a Bill."))
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) > 1:
            raise UserError(_("You can only create a withhold for only one record at a time."))
        move = self.env[active_model].browse(active_ids)
        result['reference'] = _("Tax Deduction for %s", move.name)
        print(move)
        print(move.move_type)
        if move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') or move.state != 'posted':
            raise UserError(_("Withhold must be created from Posted Customer Invoices, Customer Credit Notes, Vendor Bills or Vendor Refunds."))
        result['related_move_id'] = move.id
        return result

    reference = fields.Char(string="Reference")
    related_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice/Bill",
        readonly=True,
    )
    company_id = fields.Many2one(related='related_move_id.company_id', string="Company")
    currency_id = fields.Many2one(related='company_id.currency_id')
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
    base = fields.Monetary(string="Base Amount", compute='_compute_base', store=True, readonly=False)
    withhold_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Withhold Account"
    )
    withhold_account_ids = fields.One2many(
        comodel_name='account.account',
        compute='_compute_withhold_account_ids',
        string="Withhold Accounts",
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Withhold Tax",
        required=True,
        compute='_compute_tax_id',
        store=True,
        readonly=False,
    )
    amount = fields.Monetary(
        string="Tax Amount",
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

    @api.depends('company_id')
    def _compute_journal(self):
        for wizard in self:
            wizard.journal_id = wizard.company_id.parent_ids.withholding_journal_id[-1:] or \
                                wizard.env['account.journal'].search([*self.env['account.journal']._check_company_domain(wizard.company_id), ('type', '=', 'general')], limit=1)

    @api.depends('related_move_id')
    def _compute_withhold_account_ids(self):
        for wizard in self:
            accounts = wizard.related_move_id._get_withhold_account_by_sum().keys()
            wizard.withhold_account_ids = list(acc._origin.id for acc in accounts)

    @api.depends('related_move_id')
    def _compute_tax_id(self):
        for wizard in self:
            tax = self.env['account.tax']
            # Search for the last withhold move line that matches the account and partner
            withhold_move_line = self.env['account.move.line'].search([
                ('move_id.l10n_withholding_ref_move_id.commercial_partner_id', '=', wizard.related_move_id.commercial_partner_id.id),
                ('move_id.l10n_withholding_ref_move_id.line_ids.account_id', 'in', wizard.withhold_account_ids.ids),
                ('move_id.state', '=', 'posted'),
                ('tax_ids', '!=', False),
            ], limit=1, order='id desc')
            if withhold_move_line:
                applied_withhold_taxes = withhold_move_line.tax_ids.filtered(lambda t: t in wizard.withhold_account_ids._origin.withhold_tax_ids)
                if applied_withhold_taxes:
                    tax = applied_withhold_taxes[0]
            wizard.tax_id = tax


    @api.depends('tax_id', 'related_move_id')
    def _compute_base(self):
        for wizard in self:
            wizard.base = 0.0
            if wizard.tax_id:
                withhold_account_by_sum = wizard.related_move_id._get_withhold_account_by_sum()
                for account, amount in withhold_account_by_sum.items():
                    if wizard.tax_id in account.withhold_tax_ids:
                        wizard.base = amount

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        for wizard in self:
            tax_amount = 0.0
            if wizard.tax_id:
                taxes_res = wizard.tax_id._get_tax_details(
                    wizard.base,
                    quantity=1.0,
                    product=False,
                )
                tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            wizard.amount = abs(tax_amount)

    def _get_withhold_type(self):
        move_type = self.related_move_id.move_type
        withhold_type = {
            'out_invoice': 'out_withhold',
            'in_invoice': 'in_withhold',
            'out_refund': 'out_refund_withhold',
            'in_refund': 'in_refund_withhold',
        }[move_type]
        return withhold_type

    # ===== MOVE CREATION METHODS =====
    def action_create_and_post_withhold(self):
        self.ensure_one()
        related_move_id = self.related_move_id
        withholding_account_id = self.company_id.withholding_tax_control_account_id
        if not withholding_account_id:
            raise UserError(_("Please configure the withholding control account from the settings"))

        # Withhold creation and posting
        vals = self._prepare_withhold_header()
        move_lines = self._prepare_withhold_move_lines(withholding_account_id)
        vals['line_ids'] = [Command.create(line) for line in move_lines]
        withhold = self.with_company(self.company_id).env['account.move'].create(vals)
        withhold.action_post()

        # Reconcile withhold with related move
        wh_reconc = withhold.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        inv_reconc = related_move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
        (inv_reconc + wh_reconc).reconcile()

        withhold._message_log(
            body=Markup("%s: <a href='#' data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
                _("Withhold created from"),
                related_move_id._name,
                related_move_id.id,
                related_move_id.name
            ))
        return withhold

    def _prepare_withhold_header(self):
        """ Prepare the header for the withhold entry """
        vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'partner_id': self.related_move_id.partner_id.id,
            'move_type': 'entry',
            'ref': self.reference,
            'l10n_withholding_ref_move_id': self.related_move_id.id,
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

        partner = self.related_move_id.partner_id
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
