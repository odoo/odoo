# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import api, fields, models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    journal_id = fields.Many2one("account.journal", string="Journal", domain="[('type', '=', 'sale')]")
    order_id = fields.Many2one("sale.order")
    payment_term_id = fields.Many2one("account.payment.term", string="Payment Terms")

    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleAdvancePaymentInv, self).default_get(fields_list)
        if self._context.get("active_ids"):

            order = self.env["sale.order"].browse(self._context.get("active_ids"))[0]
            defaults["order_id"] = order.id
            defaults["payment_term_id"] = order.payment_term_id.id
            # defaults['advance_payment_method'] = self._get_advance_payment_method()

            if order.payment_term_id and order.payment_term_id.line_ids[0].value == "percent":
                # defaults['payment_term_id'] = self.env.ref('account.account_payment_term_immediate').id
                if order.invoice_count == 0:
                    defaults["advance_payment_method"] = "percentage"
                    defaults["amount"] = order.payment_term_id.line_ids[0].value_amount

            company_id = self._context.get("company_id", self.env.user.company_id.id)
            domain = [("type", "=", "sale"), ("company_id", "=", company_id)]
            # de ce as pune default jurnalul in aceeasi valuta cu oferta? ca doar de aceea vreau sa-l schimb
            # if order and order.pricelist_id and order.pricelist_id.currency_id:
            #     if order.pricelist_id.currency_id != self.env.user.company_id.currency_id:
            #         domain += [('currency_id', '=', order.pricelist_id.currency_id.id)]
            journal = self.env["account.journal"].search(domain, limit=1)
            if journal:
                defaults["journal_id"] = journal.id
        return defaults

    def create_invoices(self):
        new_self = self.with_context(default_journal_id=self.journal_id.id)
        return super(SaleAdvancePaymentInv, new_self).create_invoices()

    def _create_invoice(self, order, so_line, amount):
        new_self = self.with_context(default_journal_id=self.journal_id.id)
        invoice = super(SaleAdvancePaymentInv, new_self)._create_invoice(order, so_line, amount)

        to_currency = self.journal_id.currency_id or self.env.user.company_id.currency_id
        date_eval = invoice.date_invoice or fields.Date.context_today(self)
        from_currency = invoice.currency_id.with_context(date=date_eval)

        if from_currency != to_currency:
            invoice.write({"currency_id": to_currency.id, "date_invoice": date_eval})
            if self.advance_payment_method != "fixed":
                for line in invoice.invoice_line_ids:
                    price_unit = from_currency.compute(line.price_unit, to_currency, round=False)
                    line.write({"price_unit": price_unit})
                invoice.compute_taxes()
            else:
                for line in invoice.invoice_line_ids:
                    taxes = line.product_id.taxes_id or self.account_id.tax_ids
                    price_w_taxes = 0.0
                    for tax in taxes:
                        price_w_taxes = self.amount / (1 + tax.amount / 100)
                    line.write({"price_unit": price_w_taxes})
                    price_unit_saleorder = to_currency.compute(self.amount, from_currency, round=False)
                    sale_orders = self.env["sale.order"].browse(self._context.get("active_ids", []))
                    order_line_downpayment = False
                    for order in sale_orders:
                        order_lines = order.order_line
                        for order_line in order_lines:
                            if order_line.is_downpayment:
                                # order_line.write({'price_unit': price_unit_saleorder})
                                order_line_downpayment = order_line
                    if order_line_downpayment:
                        order_line_downpayment.write({"price_unit": price_unit_saleorder})

                invoice.compute_taxes()

        if self.advance_payment_method == "percentage":
            invoice.write({"payment_term_id": False})
        else:
            invoice.write({"payment_term_id": self.payment_term_id.id})
            invoice.write({"date_invoice": False})

        return invoice

    @api.onchange("advance_payment_method")
    def onchange_advance_payment_method(self):
        if self.advance_payment_method == "percentage":
            amount = 0.0
            order = self.order_id
            if order.payment_term_id and order.payment_term_id.line_ids[0].value == "percent":
                amount = order.payment_term_id.line_ids[0].value_amount
            return {"value": {"amount": amount}}
        return {}
