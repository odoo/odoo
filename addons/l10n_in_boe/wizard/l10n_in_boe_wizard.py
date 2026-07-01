from odoo import api, fields, models, Command


class L10n_InBoeWizard(models.TransientModel):
    _name = 'l10n_in.boe.wizard'
    _description = "Bill Of Entry Wizard"

    move_id = fields.Many2one('account.move', string="Original Entry", required=True)
    currency_id = fields.Many2one(related='move_id.company_id.currency_id', string="Currency")
    source_partner_id = fields.Many2one(related='move_id.partner_id')
    partner_id = fields.Many2one('res.partner', string="Vendor")

    picking_ids = fields.Many2many('stock.picking',
        string="Transfers",
        domain="[('state', '=', 'done'), ('picking_type_id.code', '=', 'incoming'), ('partner_id', '=', source_partner_id)]",
    )

    line_ids = fields.One2many('l10n_in.bill.of.entry.line', 'wizard_id', string="Lines")

    l10n_in_shipping_bill_number = fields.Char("Shipping Bill Number")
    l10n_in_shipping_bill_date = fields.Date("Shipping Bill Date")
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', "Port Code")

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

        custom_duty_product = self.env.ref('l10n_in_boe.product_custom_duty', raise_if_not_found=False)

        if not custom_duty_product:
            ChartTemplate = self.env['account.chart.template'].with_company(self.move_id.company_id)
            custom_duty_account = ChartTemplate.ref('p2140', raise_if_not_found=False)

            custom_duty_product = self.env['product.product'].create({
                'name': 'Custom Duty',
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': True,
                'property_account_expense_id': custom_duty_account.id if custom_duty_account else False,
                'property_account_income_id': custom_duty_account.id if custom_duty_account else False,
                'landed_cost_ok': True,
            })

            self.env['ir.model.data'].create({
                'name': 'product_custom_duty',
                'module': 'l10n_in_boe',
                'model': 'product.product',
                'res_id': custom_duty_product,
            })

        # We group by tax so that if lines have different taxes, they remain accurate.
        tax_groups = {}
        total_assessable = 0.0

        for line in self.line_ids:
            tax_id = line.tax_id.id if line.tax_id else False
            amount = line.assessable_value + line.custom_duty

            if tax_id not in tax_groups:
                tax_groups[tax_id] = {
                    'amount': 0.0,
                    'tax': line.tax_id,
                }
            tax_groups[tax_id]['amount'] += amount
            total_assessable += line.assessable_value

        invoice_lines = []

        # Sum of Assessable + Custom Duty
        for tax_id, data in tax_groups.items():
            invoice_lines.append(Command.create({
                'product_id': custom_duty_product.id,
                'name': custom_duty_product.name,
                'quantity': 1.0,
                'price_unit': data['amount'],
                'tax_ids': [Command.set(data['tax'].ids)] if data['tax'] else False,
                'is_landed_costs_line': True,
            }))

        # Sum of Assessable
        if total_assessable:
            invoice_lines.append(Command.create({
                'product_id': custom_duty_product.id,
                'name': f"{custom_duty_product.name} (Assessable Value Deduction)",
                'quantity': 1.0,
                'price_unit': -total_assessable,
                'tax_ids': False,
                'is_landed_costs_line': True,
            }))

        boe_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.l10n_in_shipping_bill_date or fields.Date.context_today(self),
            'date': self.l10n_in_shipping_bill_date or fields.Date.context_today(self),
            'ref': self.l10n_in_shipping_bill_number,
            'invoice_line_ids': invoice_lines,
            'l10n_in_shipping_bill_number': self.l10n_in_shipping_bill_number,
            'l10n_in_shipping_bill_date': self.l10n_in_shipping_bill_date,
            'l10n_in_shipping_port_code_id': self.l10n_in_shipping_port_code_id.id,
        })

        if self.picking_ids and self.total_custom_duty > 0:
            expense_account = custom_duty_product.property_account_expense_id

            self.env['stock.landed.cost'].create({
                'vendor_bill_id': boe_bill.id,
                'picking_ids': [Command.set(self.picking_ids.ids)],
                'cost_lines': [Command.create({
                    'product_id': custom_duty_product.id,
                    'name': custom_duty_product.name,
                    'account_id': expense_account.id if expense_account else False,
                    'split_method': custom_duty_product.split_method_landed_cost or 'equal',
                    'price_unit': self.total_custom_duty,
                })],
            })

        if self.partner_id:
            boe_bill.action_post()

        return {
            'name': 'Bill Of Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': boe_bill.id,
            'view_mode': 'form',
            'target': 'current',
        }


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
