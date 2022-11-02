# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Advanced Check Management',
    'version': "1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Checks Management',
    'description': """
Own Checks Management
---------------------

Extends 'Check Printing Base' module to manage own checks with more features:

* allow using own checks that are not printed but filled manually by the user
* allow to use checkbooks to track numbering
* allow to use different checkbooks type (deferred, electronic, current)
* add an optional "payment date" for post-dated checks (deferred payments)
* add a menu to track own checks
* two modifications are done when using checkbooks:

    * the next number of the check is suggested but editable by the user. This is needed for electronic checks where the next number is given by the bank and also when using pre-printed checkbooks where it's really common that the order of inputting checks in odoo is not the same as the numbering
    * the printing functionality is disabled because there is not standard format and a report for each bank should be implemented. It's a nice to have that could be implemented by customization if needed


Third Party Checks Management
-----------------------------

Add new "Third party check Management" feature.

There are 2 main Payment Methods additions:

* New Third party checks:

   * allow the user create a check on the fly from a payment
   * create a third party check from a customer payment

* Third party check:

   * allow the user to reuse a Third party check already created
   * pay a vendor bill using an existing Third party check
   * move an existing checks between journals (i.e. move to Rejected)
   * Send/Receive again a check already used in a Vendor Bill/Customer INV
   * allow the user to do mass check transfers

""",
    'author': 'ADHOC SA',
    'license': 'LGPL-3',
    'images': [
    ],
    'depends': [
        'account_check_printing',
        'base_vat',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'views/account_journal_view.xml',
        'wizards/account_payment_register_views.xml',
        'wizards/l10n_latam_payment_mass_transfer_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
