from odoo import Command
from odoo.tests import TransactionCase


class BaseTaxCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country = cls.company.country_id or cls.env.ref("base.us")
        if not cls.company.country_id:
            cls.company.country_id = cls.country
        cls.tax_group = cls.env["account.tax.group"].create(
            {
                "name": "account_tax test group",
                "company_ids": [Command.set(cls.company.ids)],
                "country_id": cls.country.id,
            }
        )
        cls.currency = cls.company.currency_id
        cls.account_installed = "account_config_id" in cls.env["res.company"]._fields

    _seq = 0

    @classmethod
    def _tax(cls, amount, amount_type="percent", **kw):
        cls._seq += 1
        kw.setdefault("name", f"BT test tax {cls._seq}")
        kw.setdefault("type_tax_use", "sale")
        kw.setdefault("country_id", cls.country.id)
        kw.setdefault("tax_group_id", cls.tax_group.id)
        return cls.env["account.tax"].create(
            {"amount_type": amount_type, "amount": amount, **kw}
        )

    def _base_line(self, taxes, price_unit, quantity=1.0, **kw):
        kw.setdefault("company_id", self.company)
        kw.setdefault("currency_id", self.currency)
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            None,
            tax_ids=taxes,
            price_unit=price_unit,
            quantity=quantity,
            **kw,
        )
