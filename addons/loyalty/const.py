# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment providers (and of their payment methods and account payment methods)
# allowing to pay with the balance of a loyalty card. Each code is also the program type whose cards
# can be used with the provider.
LOYALTY_PAYMENT_CODES = ("gift_card", "ewallet")

# The xmlid (without the `account.<company_id>_` prefix) of the liability account holding the value
# of the sold gift cards and eWallet top-ups until they are spent.
LOYALTY_LIABILITY_ACCOUNT_XMLID = "loyalty_liability_account"
