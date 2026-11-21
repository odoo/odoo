# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment providers (and of their payment methods and account payment methods)
# allowing to pay with the balance of a loyalty card. Each code is also the program type whose cards
# can be used with the provider.
LOYALTY_PAYMENT_CODES = ("gift_card", "ewallet")

# Company-specific xmlid suffix for the liability account holding card balances.
LOYALTY_LIABILITY_ACCOUNT_XMLID = "loyalty_liability_account"
