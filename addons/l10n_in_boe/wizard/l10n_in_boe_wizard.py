from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class L10n_InBoeWizard(models.TransientModel):
    _name = 'l10n_in.boe.wizard'
    _description = "Bill Of Entry Wizard"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        move_ids = self.env.context.get('default_move_ids')
        if move_ids:
            moves = self.env['account.move'].browse(move_ids)
            self._check_valid_boe_moves(moves)

        return defaults

    move_ids = fields.Many2many('account.move', string="Original Entry", required=True)
    company_currency_id = fields.Many2one('res.currency', compute="_compute_move_defaults", string="Company Currency")
    currency_id = fields.Many2one('res.currency', compute="_compute_move_defaults", readonly=False, string="Document Currency")
    source_partner_id = fields.Many2one('res.partner', compute="_compute_move_defaults")

    invoice_currency_rate = fields.Float(
        string="Currency Rate",
        compute="_compute_invoice_currency_rate",
        readonly=False,
        store=True,
    )

    picking_ids = fields.Many2many('stock.picking',
        string="Transfers",
        compute="_compute_picking_ids",
        readonly=False,
        store=True,
        domain="[('state', '=', 'done'), ('picking_type_id.code', '=', 'incoming'), ('partner_id.commercial_partner_id', '=', source_partner_id)]",
    )

    line_ids = fields.One2many(
        'l10n_in.boe.wizard.line',
        'wizard_id',
        string="Lines",
        compute="_compute_line_ids",
        store=True,
        readonly=False,
    )

    l10n_in_shipping_bill_number = fields.Char("Shipping Bill Number")
    l10n_in_shipping_bill_date = fields.Date("Shipping Bill Date")
    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', "Port Code")

    total_custom_duty = fields.Monetary(compute="_compute_amount", currency_field='company_currency_id')
    total_tax = fields.Monetary(compute="_compute_amount", currency_field='company_currency_id')
    total_amount = fields.Monetary(compute="_compute_amount", currency_field='company_currency_id')

    @api.depends('move_ids')
    def _compute_move_defaults(self):
        for wizard in self:
            wizard.company_currency_id = wizard.move_ids.company_id.currency_id
            wizard.currency_id = wizard.move_ids.currency_id
            wizard.source_partner_id = wizard.move_ids.commercial_partner_id

    @api.depends('move_ids')
    def _compute_picking_ids(self):
        for wizard in self:
            purchase_orders = wizard.move_ids.invoice_line_ids.purchase_line_id.order_id
            valid_pickings = purchase_orders.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_id.code == 'incoming',
            )
            wizard.picking_ids = valid_pickings

    @api.depends('move_ids', 'l10n_in_shipping_bill_date', 'currency_id')
    def _compute_invoice_currency_rate(self):
        for wizard in self:
            wizard.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=wizard.company_currency_id,
                to_currency=wizard.currency_id,
                company=wizard.move_ids.company_id,
                date=wizard.l10n_in_shipping_bill_date or fields.Date.today(),
            )

    @api.depends('line_ids.custom_duty', 'line_ids.tax_amount')
    def _compute_amount(self):
        for wizard in self:
            wizard.total_custom_duty = sum(wizard.line_ids.mapped('custom_duty'))
            wizard.total_tax = sum(wizard.line_ids.mapped('tax_amount'))
            wizard.total_amount = wizard.total_custom_duty + wizard.total_tax

    @api.depends('picking_ids', 'invoice_currency_rate')
    def _compute_line_ids(self):
        for wizard in self:
            product_unit_prices = {}  # we try to get the assessable_value from move (bill) if there is.
            for line in wizard.move_ids.invoice_line_ids:
                if line.quantity and line.purchase_line_id:
                    product_unit_prices[line] = float_round(line.price_subtotal / line.quantity, 2)

            preserved_data = {}
            for line in wizard.line_ids:
                if line.stock_move_id:
                    preserved_data[line.stock_move_id.id] = {
                        'custom_duty': line.custom_duty,
                        'tax_ids': line.tax_ids.ids,
                    }

            rate = wizard.invoice_currency_rate
            lines_vals = [Command.clear()]

            for move in wizard.picking_ids.move_ids:
                move_id = move._origin.id or move.id
                invoice_lines = move.purchase_line_id.invoice_lines
                if invoice_lines:
                    unit_price = float_round(
                        sum(product_unit_prices.get(aml, move.purchase_line_id.price_unit) for aml in invoice_lines) / len(invoice_lines)
                    , 2)
                else:
                    unit_price = move.purchase_line_id.price_unit
                old_data = preserved_data.get(move_id, {})
                vals = {
                    'stock_move_id': move.id,
                    'product_id': move.product_id.id,
                    'assessable_value': (unit_price * move.quantity) / rate if rate else 0,
                    # Restore previous user entries if the move already existed
                    'custom_duty': old_data.get('custom_duty', 0.0),
                    'tax_ids': [Command.set(old_data.get('tax_ids', []))],
                }

                lines_vals.append(Command.create(vals))

            wizard.line_ids = lines_vals

    @api.constrains('move_ids')
    def _check_move_ids(self):
        for wizard in self:
            if wizard.move_ids:
                wizard._check_valid_boe_moves(wizard.move_ids)

    def action_on_submit_boe(self):
        self.ensure_one()

        if any(product.cost_method not in ('fifo', 'average') for product in self.line_ids.product_id):
            raise UserError(
                self.env._(
                    "You cannot apply landed costs on the chosen transfers\n"
                    "Landed costs can only be applied for products with FIFO or average costing method.",
                ),
            )

        custom_duty_product = self._get_l10n_in_find_or_create_custom_duty_product()
        custom_duty_account = custom_duty_product.product_tmpl_id.get_product_accounts().get('expense')

        # We group by tax so that if lines have different taxes, they remain accurate.
        tax_groups = {}
        total_assessable = 0.0

        for line in self.line_ids:
            tax_groups[line.tax_ids] = tax_groups.get(line.tax_ids, 0.0) + line.assessable_value + line.custom_duty
            total_assessable += line.assessable_value

        # Sum of Assessable + Custom Duty
        invoice_lines = [
            Command.create({
                'product_id': custom_duty_product.id,
                'quantity': 1.0,
                'account_id': custom_duty_account.id,
                'price_unit': amount,
                'tax_ids': [Command.set(tax_ids.ids)],
                'is_landed_costs_line': True,
            })
            for tax_ids, amount in tax_groups.items()
        ]

        # Sum of Assessable
        if total_assessable:
            invoice_lines.append(Command.create({
                'product_id': custom_duty_product.id,
                'name': f"{custom_duty_product.name} (Assessable Value Deduction)",
                'quantity': 1.0,
                'account_id': custom_duty_account.id,
                'price_unit': -total_assessable,
                'tax_ids': False,
                'is_landed_costs_line': True,
            }))

        shipping_bill_date = self.l10n_in_shipping_bill_date or fields.Date.context_today(self)

        boe_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': shipping_bill_date,
            'date': shipping_bill_date,
            'ref': self.l10n_in_shipping_bill_number,
            'invoice_line_ids': invoice_lines,
            'l10n_in_shipping_bill_number': self.l10n_in_shipping_bill_number,
            'l10n_in_shipping_bill_date': self.l10n_in_shipping_bill_date,
            'l10n_in_shipping_port_code_id': self.l10n_in_shipping_port_code_id.id,
        })

        landed_cost = self.env['stock.landed.cost'].sudo().create({
            'vendor_bill_id': boe_bill.id,
            'picking_ids': [Command.set(self.picking_ids.ids)],
            'cost_lines': [Command.create({
                'product_id': custom_duty_product.id,
                'name': custom_duty_product.name,
                'account_id': custom_duty_account.id,
                'split_method': custom_duty_product.split_method_landed_cost or 'equal',
                'price_unit': self.total_custom_duty,
            })],
        })

        cost_line = landed_cost.cost_lines[0]
        valuation_lines = []

        for boe_line in self.line_ids:
            stock_move = boe_line.stock_move_id

            if stock_move and boe_line.custom_duty:
                valuation_lines.append(Command.create({
                    'cost_id': landed_cost.id,
                    'cost_line_id': cost_line.id,
                    'move_id': stock_move.id,
                    'product_id': boe_line.product_id.id,
                    'quantity': stock_move.quantity,
                    'former_cost': boe_line.assessable_value,
                    'additional_landed_cost': boe_line.custom_duty,
                }))

        if valuation_lines:
            landed_cost.write({'valuation_adjustment_lines': valuation_lines})

        self.move_ids.write({
            'l10n_in_shipping_bill_number': self.l10n_in_shipping_bill_number,
            'l10n_in_shipping_bill_date': self.l10n_in_shipping_bill_date,
            'l10n_in_shipping_port_code_id': self.l10n_in_shipping_port_code_id,
        })

        message = self.env._("Bill of Entry is created: ") + boe_bill._get_html_link(title="BOE")
        self.move_ids._message_log_batch(
            bodies={move.id: message for move in self.move_ids},
        )

        return boe_bill._get_records_action()

    # Other business/helper methods
    def _check_valid_boe_moves(self, moves):
        if len(moves.company_id) > 1:
            raise UserError(self.env._(
                "All selected records must belong to the same company to create a Bill of Entry.",
            ))

        if len(moves.commercial_partner_id) > 1:
            raise UserError(self.env._(
                "All selected records must belong to the same vendor to create a Bill of Entry.",
            ))

        if len(moves.currency_id) > 1:
            raise UserError(self.env._(
                "All selected records must have same document currency to create a Bill of Entry.",
            ))

        if any(move.move_type != 'in_invoice' or move.state != 'posted' or move.l10n_in_gst_treatment != 'overseas' for move in moves):
            raise UserError(self.env._(
                "You can only create a Bill of Entry for posted Vendor Bills with an 'Overseas' GST Treatment.",
            ))

    def _get_l10n_in_find_or_create_custom_duty_product(self):
        custom_duty_product = self.env.ref('l10n_in_boe.product_custom_duty', raise_if_not_found=False)
        if not custom_duty_product:
            custom_duty_product = self.env['product.product'].sudo().create({
                'name': self.env._("Custom Duty"),
                'type': 'service',
                'purchase_ok': True,
                'sale_ok': False,
                'landed_cost_ok': True,
                'taxes_id': [],
                'supplier_taxes_id': [],
            })

            self.env['ir.model.data']._update_xmlids([{
                'xml_id': 'l10n_in_boe.product_custom_duty',
                'record': custom_duty_product,
                'noupdate': True,
            }])
        return custom_duty_product


class BillOfEntryLine(models.TransientModel):
    _name = 'l10n_in.boe.wizard.line'
    _description = 'Bill of Entry Line Wizard'

    wizard_id = fields.Many2one('l10n_in.boe.wizard')
    product_id = fields.Many2one('product.product')
    stock_move_id = fields.Many2one('stock.move', string="Stock Move")
    quantity = fields.Float(string="Quantity", related='stock_move_id.quantity')
    assessable_value = fields.Monetary()
    custom_duty = fields.Monetary()
    tax_ids = fields.Many2many("account.tax", domain="[('type_tax_use', '=', 'purchase')]")
    taxable_amount = fields.Monetary(compute="_compute_amounts")
    tax_amount = fields.Monetary(compute="_compute_amounts")
    currency_id = fields.Many2one(related='wizard_id.company_currency_id')

    @api.depends('assessable_value', 'custom_duty', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            line.taxable_amount = line.assessable_value + line.custom_duty
            if line.tax_ids and line.taxable_amount:
                taxes = line.tax_ids.compute_all(line.taxable_amount, product=line.product_id)
                line.tax_amount = taxes['total_included'] - taxes['total_excluded']
            else:
                line.tax_amount = 0.0
