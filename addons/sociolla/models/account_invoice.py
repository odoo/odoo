from openerp import api, fields, models, _

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Vendor Refund
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    price_undiscounted = fields.Monetary(string='Undiscount Amount', store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount(self):
        super(AccountInvoice,self)._compute_amount()
        self.price_undiscounted = sum(line.price_undiscounted for line in self.invoice_line_ids)
        self.discount_amount = sum(line.discount_amount for line in self.invoice_line_ids)

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and
            # analytic lines)
            iml = inv.invoice_line_move_line_get() # sales account
            iml += inv.tax_line_move_line_get() # tax account

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other
            # lines amount
            total, total_currency, total_discount, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            price_amount = total
            if self.type in ('out_invoice', 'out_refund'):
                price_amount -= total_discount

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=inv.currency_id.id).compute(price_amount, date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'discount_amount': 0,
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': price_amount,
                    'discount_amount': 0,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })

            # Journla Sales will record account Sales Discount
            if self.type in ('out_invoice', 'out_refund'):
                iml += inv.discount_line_move_line_get()

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['dont_create_taxes'] = True
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get
            # the same
            # account move reference when creating the same invoice after a
            # cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))

            price_amount = line.price_subtotal
            discount_amount = 0

            # Journal sales for account income the amount will be add discount_amount
            if self.type in ('out_invoice', 'out_refund'):
                price_amount += line.discount_amount
                discount_amount = line.discount_amount

            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': price_amount,
                'discount_amount': discount_amount,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
            }
            if line['account_analytic_id']:
                move_line_dict['analytic_line_ids'] = [(0, 0, line._get_analytic_line())]
            res.append(move_line_dict)
            
        return res

    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            if tax_line.amount:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                done_taxes.append(tax.id)
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount,
                    'discount_amount': 0,
                    'quantity': 1,
                    'price': tax_line.amount,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, done_taxes)] if tax_line.tax_id.include_base_amount else []
                })
        return res

    @api.model
    def discount_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            if line.discount_amount > 0:
                amount = line.discount_amount

                if self.type == 'out_refund':
                    amount = - line.discount_amount

                move_line_dict = {
                    'invl_id': line.id,
                    'type': 'disc',
                    'name': 'Sales Discount ' + line.name.split('\n')[0][:64],
                    'price_unit': line.price_unit,
                    'quantity': line.quantity,
                    'price':amount,
                    'discount_amount':0,
                    'account_id': line.discount_account_id.id,
                    'product_id': line.product_id.id,
                    'uom_id': line.uom_id.id,
                    'account_analytic_id': line.account_analytic_id.id,
                    'invoice_id': self.id,
                }
                if line['account_analytic_id']:
                    move_line_dict['analytic_line_ids'] = [(0, 0, line._get_analytic_line())]
                res.append(move_line_dict)
            
        return res

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        total = 0
        total_currency = 0
        total_discount = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = currency.round(line['price'])
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])

            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_discount += line['discount_amount']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_discount -= line['discount_amount']
                total_currency -= line['amount_currency'] or line['price']

        return total, total_currency, total_discount, invoice_move_lines

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.iteritems():
                if name in MAGIC_COLUMNS:
                    continue
                elif name == 'account_id':
                    if TYPE2REFUND[line.invoice_id.type] == 'out_refund':
                        account = line.get_invoice_line_account('out_refund', line.product_id, line.invoice_id.fiscal_position_id, line.invoice_id.company_id)
                        if account:
                            values[name] = account.id
                        else:
                            raise UserError(_('Configuration error!\nCould not find any account to create the return, are you sure you have a chart of account installed?'))
                    else:
                        values[name] = line[name].id
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_ids':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_price')
    price_undiscounted = fields.Monetary(string='Undiscount Amount', store=True, readonly=True, compute='_compute_price')
    discount_account_id = fields.Many2one('account.account', string='Discount Account', domain=[('deprecated', '=', False)])

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        self.price_undiscounted = self.price_unit * self.quantity
        self.discount_amount = self.price_undiscounted * ((self.discount or 0.0) / 100.0)

        super(AccountInvoiceLine,self)._compute_price()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.invoice_id:
            return

        domain = super(AccountInvoiceLine, self)._onchange_product_id()

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            account = product.product_tmpl_id.get_product_accounts()
            if account:
                self.discount_account_id = account['sales_discount']
            else:
                raise UserError(_('Configuration error!\nCould not find any account to create the discount, are you sure you have a chart of account installed?'))

    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type == 'out_invoice':
            return accounts['income']
        elif type == 'out_refund':
            return accounts['sales_return']

        return accounts['expense']
