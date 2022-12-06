# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Third Party and Deferred/Electronic Checks Management',
    'version': "1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Checks Management',
    'description': """
Own Checks Management
---------------------

Extends 'Check Printing Base' module to manage own checks with more features:

* allow using own checks that are not printed but filled manually by the user
* allow to use deferred or electronic checks
  * printing is disabled
  * check number is set manually by the user
* add an optional "Check Cash-In Date" for post-dated checks (deferred payments)
* add a menu to track own checks

Third Party Checks Management
-----------------------------

Add new "Third party check Management" feature.

There are 2 main Payment Methods additions:

* New Third Party Checks:

  * Payments of this payment method represent the check you get from a customer when getting paid (from an invoice or a manual payment)

* Existing Third Party check.

  * Payments of this payment method are to track moves of the check, for eg:

    * Use a check to pay a vendor
    * Deposit the check on the bank
    * Get the check back from the bank (rejection)
    * Get the check back from the vendor (a rejection or return)
    * Transfer the check from one third party check journal to the other (one shop to another)

  * Those operations can be done with multiple checks at once
""",
    'author': 'ADHOC SA',
    'license': 'LGPL-3',
    'depends': [
        'account_check_printing',
        'base_vat',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'wizards/l10n_latam_payment_mass_transfer_views.xml',
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/account_journal_view.xml',
        'wizards/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
