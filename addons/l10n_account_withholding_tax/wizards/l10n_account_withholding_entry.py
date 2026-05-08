from odoo import api, Command, fields, models
from odoo.exceptions import ValidationError, UserError


class L10nAccountWithholdingEntry(models.TransientModel):
    _name = 'l10n.account.withholding.entry'
    _description = "Withhold Wizard"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        active_model = self.env.context.get('active_model')
        if active_model != 'account.move':
            raise UserError(self.env._("You can only create a withhold for a Bill."))
        active_ids = self.env.context.get('active_ids', [])
        if len(active_ids) > 1:
            raise UserError(self.env._("You can only create a withhold for only one record at a time."))
        move = self.env[active_model].browse(active_ids)
        result['reference'] = self.env._("Tax Deduction for %s", move.name)
        if move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') or move.state != 'posted':
            raise UserError(self.env._("Withhold must be created from Posted Customer Invoices, Customer Credit Notes, Vendor Bills or Vendor Refunds."))
        result['related_move_id'] = move.id
        return result

    reference = fields.Char(string="Reference")
    related_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Invoice/Bill",
        readonly=True,
    )
    company_id = fields.Many2one(related='related_move_id.company_id', string="Company")
    currency_id = fields.Many2one(related='related_move_id.currency_id', string="Currency")
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
    withholding_line_ids = fields.One2many(
        string="Withholding Lines",
        comodel_name='l10n.account.withholding.entry.line',
        compute='_compute_withholding_line_ids',
        inverse_name='withholding_entry_id',
        store=True,
        readonly=False,
    )

    @api.depends('company_id')
    def _compute_journal(self):
        for wizard in self:
            wizard.journal_id = wizard.company_id.parent_ids.withholding_journal_id[-1:] or \
                wizard.env['account.journal'].search([*self.env['account.journal']._check_company_domain(wizard.company_id), ('type', '=', 'general')], limit=1)

    def _compute_withholding_line_ids(self):
        for wizard in self:
            # Compute the lines themselves once; when opening the wizard.
            if not wizard.withholding_line_ids:
                base_lines = []
                for move in wizard.related_move_id:
                    move_base_lines, _move_tax_lines = move._get_rounded_base_and_tax_lines()
                    base_lines += move_base_lines

                wizard.withholding_line_ids = wizard.withholding_line_ids._prepare_withholding_lines_commands(
                    base_lines=base_lines,
                    company=wizard.company_id or self.env.company,
                )

    @api.onchange('withholding_line_ids')
    def _onchange_withholding_line_ids(self):
        """
        Any time a line is edited, we want to check if we need to recompute the placeholders.
        The idea is to try and display accurate placeholders on lines whose tax have a sequence set.
        """
        self.ensure_one()
        if not self.withholding_line_ids._need_update_withholding_lines_placeholder():
            return

        self.withholding_line_ids._update_placeholders()

    def _get_withhold_type(self):
        move_type = self.related_move_id.move_type
        withhold_type = {
            'out_invoice': 'out_withhold',
            'in_invoice': 'in_withhold',
            'out_refund': 'out_refund_withhold',
            'in_refund': 'in_refund_withhold',
        }[move_type]
        return withhold_type

    def action_create_and_post_withhold(self):
        self.ensure_one()
        withholding_account_id = self.company_id.withholding_tax_base_account_id
        self._validate_withhold_data_on_post(withholding_account_id)

        # Withhold creation and posting
        vals = self._prepare_withhold_header()
        move_lines = self.withholding_line_ids._prepare_withholding_amls_create_values()
        vals['line_ids'] = [Command.create(line) for line in move_lines]
        withhold = self.env['account.move'].create(vals)
        withhold.action_post()

        # If the withhold is created from a payment, there is no need to reconcile
        wh_reconc = withhold.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))
        inv_reconc = self.related_move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled)
        (inv_reconc + wh_reconc).reconcile()
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

    def _validate_withhold_data_on_post(self, withholding_account_id):
        if not withholding_account_id:
            raise UserError(self.env._("Please configure the withholding account from the settings"))
        if not self.withholding_line_ids:
            raise ValidationError(self.env._("You must input at least one withhold line"))
