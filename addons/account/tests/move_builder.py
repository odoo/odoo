from odoo.fields import Command


class _BaseBuilder:
    def __init__(self, env, model_name):
        self.env = env
        self.model_name = model_name
        self.values = {}

    def build(self):
        return self.env[self.model_name].create(self.values)


class MoveBuilder(_BaseBuilder):
    def __init__(self, env, partner=None):
        super().__init__(env, "account.move")
        if partner:
            self.values["partner_id"] = partner.id

    def out_invoice(self):
        self.values["move_type"] = "out_invoice"
        return self

    def in_invoice(self):
        self.values["move_type"] = "in_invoice"
        return self

    def out_refund(self):
        self.values["move_type"] = "out_refund"
        return self

    def in_refund(self):
        self.values["move_type"] = "in_refund"
        return self

    def on(self, date_str, /):
        self.values["date"] = date_str
        self.values["invoice_date"] = date_str
        return self

    def currency(self, currency, /):
        self.values["currency_id"] = currency.id
        return self

    def line(self, *, product, price_unit, taxes=None, **extra):
        vals = {
            "product_id": product.id,
            "price_unit": price_unit,
            "tax_ids": [Command.set([] if not taxes else taxes.ids)]
        }
        if extra:
            vals.update(extra)
        self.values.setdefault("invoice_line_ids", []).append(Command.create(vals))
        return self

    def post(self):
        move = self.build()
        move.action_post()
        return move


class PaymentBuilder(_BaseBuilder):
    def __init__(self, env, partner=None):
        super().__init__(env, "account.payment")
        if partner:
            self.values["partner_id"] = partner.id

    def inbound(self):
        self.values["payment_type"] = "inbound"
        self.values["partner_type"] = "customer"
        return self

    def on(self, date_str, /):
        self.values["date"] = date_str
        return self

    def amount(self, value, /):
        self.values["amount"] = value
        return self

    def post(self):
        p = self.build()
        p.action_post()
        return p


class Builders:
    def __init__(self, env, partner=None):
        self.env = env
        self.default_partner = partner

    @property
    def move(self):
        return MoveBuilder(self.env, partner=self.default_partner)

    @property
    def payment(self):
        return PaymentBuilder(self.env, partner=self.default_partner)

    def reverse_move(self, move, *, reason="no reason", journal=None):
        ctx = {"active_model": "account.move", "active_ids": move.ids}
        values = {"reason": reason, "journal_id": (journal or move.journal_id).id}
        reversal = move.env["account.move.reversal"].with_context(**ctx).create(values)
        action = reversal.refund_moves()
        return move.env["account.move"].browse(action["res_id"])
