from odoo import models, fields, api, Command


class L10n_InBoeWizard(models.TransientModel):
    _name = 'l10n_in.boe.wizard'
    _description = "Bill Of Entry Wizard"

    move_id = fields.Many2one('account.move', string="Original Entry", required=True)
    currency_id = fields.Many2one(related='move_id.company_id.currency_id', string="Currency")

    line_ids = fields.One2many('l10n_in.bill.of.entry.line', 'wizard_id', string="Lines")

    l10n_in_shipping_bill_number = fields.Char("Shipping Bill Number")
    l10n_in_shipping_bill_date = fields.Date("Shipping Bill Date")
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', "Port Code")

    l10n_in_boe_journal_id = fields.Many2one(
        'account.journal',
        string="BOE Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
    )

    total_custom_duty = fields.Monetary(compute="_compute_amount")
    total_tax = fields.Monetary(compute="_compute_amount")
    total_amount = fields.Monetary(compute="_compute_amount")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        move = self.env['account.move'].browse(self.env.context.get('default_move_id'))
        if not move:
            return res

        lines = []
        for line in move.invoice_line_ids:

            lines.append(Command.create({
                'product_id': line.product_id.id,
                # Assessable value must be in company currency (INR).
                # price_subtotal is in invoice currency, so convert using invoice_currency_rate.
                'assessable_value': line.price_subtotal / move.invoice_currency_rate,
            }))

        res['line_ids'] = lines
        return res

    @api.depends('line_ids.custom_duty', 'line_ids.tax_amount')
    def _compute_amount(self):
        for wizard in self:
            wizard.total_custom_duty = sum(wizard.line_ids.mapped('custom_duty'))
            wizard.total_tax = sum(wizard.line_ids.mapped('tax_amount'))
            wizard.total_amount = wizard.total_custom_duty + wizard.total_tax

    def action_on_submit_boe(self):
        self.ensure_one()

        boe_move = self.env['account.move'].create({
            'date': self.l10n_in_shipping_bill_date or fields.Date.context_today(self),
            'move_type': 'entry',
            'journal_id': self.l10n_in_boe_journal_id.id,
            'partner_id': self.move_id.partner_id.id,
            'ref': f"BOE - {self.move_id.name}",

            # Identify it as a BOE entry and link the source
            'l10n_in_source_bill_id': self.move_id.id,

            'l10n_in_shipping_bill_number': self.l10n_in_shipping_bill_number,
            'l10n_in_shipping_bill_date': self.l10n_in_shipping_bill_date,
            'l10n_in_shipping_port_code_id': self.l10n_in_shipping_port_code_id.id if self.l10n_in_shipping_port_code_id else False,

            'l10n_in_boe_line_ids': [Command.create({
                'product_id': line.product_id.id,
                'assessable_value': line.assessable_value,
                'custom_duty': line.custom_duty,
                'tax_id': line.tax_id.id,
            }) for line in self.line_ids],
        })

        boe_move.line_ids = [
            Command.create(vals) for vals in boe_move._prepare_l10n_in_boe_move_lines_vals()
        ]

        boe_move.action_post()


class BillOfEntryLine(models.TransientModel):
    _name = 'l10n_in.bill.of.entry.line'
    _description = 'Bill of Entry Line Wizard'

    wizard_id = fields.Many2one('l10n_in.boe.wizard')
    product_id = fields.Many2one('product.product')
    assessable_value = fields.Monetary()
    custom_duty = fields.Monetary()
    tax_id = fields.Many2one("account.tax", domain="[('type_tax_use', '=', 'purchase')]")
    taxable_amount = fields.Monetary(compute="_compute_amounts")
    tax_amount = fields.Monetary(compute="_compute_amounts")
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('assessable_value', 'custom_duty', 'tax_id')
    def _compute_amounts(self):
        for line in self:
            line.taxable_amount = line.assessable_value + line.custom_duty
            if line.tax_id and line.taxable_amount:
                taxes = line.tax_id.compute_all(line.taxable_amount, product=line.product_id)
                line.tax_amount = taxes['total_included'] - taxes['total_excluded']
            else:
                line.tax_amount = 0.0
