# Security review: [IMP] payment: pay with a card saved by a colleague

## High - the PR widens the token ownership check to same-company, which any partner without a company satisfies

addons/payment/controllers/portal.py, `PaymentPortal._create_transaction`,
the `flow == 'token'` branch.

The PR reworks the check that prevents paying with a token that doesn't
belong to the paying partner: instead of comparing the paying partner's
commercial partner with the token partner's commercial partner, it now
also allows the payment when the two partners belong to the same company
(`partner.company_id != token.partner.company_id` added as a second
condition).

That second condition is satisfied by any two partners whose `company_id`
is unset — and `company_id` is a plain Many2one that most customer
partners don't have. Two unset companies compare equal, so
`company_id != company_id` is False and the check never raises: any
customer can charge any other customer's saved card through
`/payment/transaction`, with their own access token (it authenticates
the paying partner, not the token owner) and the victim's `token_id`.
This brings back CVE-2021-23178, fixed by odoo/odoo 9a063023f9f7.

The multi-company test cases pass: those partners have companies, and
the comparison behaves for them.

Fix: drop the company comparison and restore the partner-level check, or
require the token partner to be the paying partner's commercial partner
or a contact of it. Company-level equality is not an ownership relation
between customer partners.

## Not issues

- The company story itself (an employee paying with a card saved by a
  colleague of the same company) is a legitimate feature; the flaw is
  that the comparison does not express it.
- Browsing the token with sudo is unchanged by the PR and is needed to
  read the token partner; the ownership check it feeds is the issue.
