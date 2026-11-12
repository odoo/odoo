# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.loyalty.const import LOYALTY_LIABILITY_ACCOUNT_XMLID


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
