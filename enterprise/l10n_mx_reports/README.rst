Electronic Accounting for Mexico and Fiscal Reports
===================================================

Add the financial reports to Mexican Electronic Invoice

- COA
- Trial Balance
- Journal Items

Add other operative reports like DIOT.

- DIOT

Known leak of features:

- Save the generated xml in order to make available an history of Fiscal declared documents.
- Unit tests to increase the coverage of this module and avoid regressions in the future.

Notes:
------

  - In the taxes could be set the account `Base Tax Received Account` that is the
    account that will be set on lines created in cash basis journal entry and
    used to keep track of the tax base amount, this account is not considered in
    the Mexican reports.

Configuration
=============

To configure this module, it is strongly recommended your chart of account depends of the l10n_mx data and structure,
you can set this afterwards if you CoA do not depends of what l10n_mx does, but you will need extra manual work.

Credits
=======

**Contributors**

* Nhomar Hernandez <nhomar@vauxoo.com> (Planner/Auditor)
* Luis Torres <luis_t@vauxoo.com> (Developer)
