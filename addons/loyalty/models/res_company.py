# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.loyalty.const import LOYALTY_LIABILITY_ACCOUNT_XMLID, LOYALTY_PAYMENT_CODES


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_loyalty_liability_account(self, create=True):
        """Return the liability account holding the value of sold gift cards and eWallet top-ups.

        The account is created on the root company the first time it is requested, provided that a
        chart of accounts is installed.

        :param bool create: Whether the account should be created if it doesn't exist yet.
        :return: The liability account, if any.
        :rtype: account.account
        """
        self.ensure_one()
        root_company = self.root_id
        chart_template = self.env["account.chart.template"].with_company(root_company)
        xmlid = chart_template.company_xmlid(LOYALTY_LIABILITY_ACCOUNT_XMLID, root_company)
        account = self.env.ref(xmlid, raise_if_not_found=False)
        if account or not create or not root_company.chart_template:
            return account or self.env["account.account"]

        Account = self.env["account.account"].sudo().with_company(root_company)
        reference_account = Account.search(
            [
                *Account._check_company_domain(root_company),
                ("account_type", "=", "liability_current"),
            ],
            order="code desc",
            limit=1,
        )
        code = Account._search_new_account_code(reference_account.code or "200000")
        return Account._load_records([
            {
                "xml_id": xmlid,
                "values": {
                    "name": self.env._("Gift Cards & eWallets"),
                    "code": code,
                    "account_type": "liability_current",
                    "company_ids": [root_company.id],
                },
                "noupdate": True,
            }
        ])

    def _setup_loyalty_accounting(self):
        """Configure the accounting of gift cards and eWallets.

        - The gift card and eWallet top-up products are sold on the liability account, as their
          value is owed to the customer until it is spent.
        - The payment method lines of the loyalty providers use that same liability account so that
          paying with a card consumes the liability instead of receiving money.
        """
        loyalty_products = self.env["product.product"].browse([
            product.id
            for xmlid in ("loyalty.gift_card_product_50", "loyalty.ewallet_product_50")
            if (product := self.env.ref(xmlid, raise_if_not_found=False))
        ])
        for company in self:
            account = company._get_loyalty_liability_account()
            if not account:
                continue
            loyalty_products.product_tmpl_id.with_company(company).sudo().write({
                "property_account_income_id": account.id
            })
            providers = (
                self
                .env["payment.provider"]
                .sudo()
                .search([("code", "in", LOYALTY_PAYMENT_CODES), ("company_id", "=", company.id)])
            )
            self.env["account.payment.method.line"].sudo().search([
                ("payment_provider_id", "in", providers.ids)
            ]).payment_account_id = account
