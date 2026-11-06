16.0.5.1.9 (2024-02-09)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Restore compatibility with python 3.9 (`#590 <https://github.com/OCA/mis-builder/issues/590>`_)


16.0.5.1.8 (2024-02-08)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Resolve a permission issue when creating report periods with a user without admin rights. (`#596 <https://github.com/OCA/mis-builder/issues/596>`_)


16.0.5.1.0 (2023-04-04)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- Improve UX by adding the option to edit the pivot date directly on the view.

16.0.5.0.0 (2023-04-01)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- Migration to 16.0

  - Addition of a generic filter domain on reports and columns.
  - Addition of a search bar to the widget. The corresponding search view is configurable
    per report.
  - Huge improvement of the widget style. This was long overdue.
  - Make the MIS Report menu accessible to the Billing Administrator group
    (instead of the hidden Show Full Accounting Features), to align with the access rules
    and avoid giving a false sense of security. This also makes the menu discoverable to
    new users.
  - Removal of analytic fetures because the upstream ``analytic_distribution`` mechanism
    is not compatible; support may be introduced in separate module, depending on use
    cases.
  - Abandon the ``mis_report_filters`` context key which had security implication.
    It is replaced by a ``mis_analytic_domain`` context key which is ANDed with other
    report-defined filters. (`#472 <https://github.com/OCA/mis-builder/issues/472>`_)
  - Rename the ``get_filter_descriptions_from_context`` method to
    ``get_filter_descriptions``. This method may be overridden to provide additional
    subtitles on the PDF or XLS report, representing user-selected filters.
  - The ``hide_analytic_filters`` has been replaced by ``widget_show_filters``.
  - The visibility of the settings button on the widget is now controlled by a
    ``show_settings_button``. Before it was visible only for the ``account_user`` group
    but this was not flexible enough.
  - The widget configuration settings are now grouped in a dedicated ``Widget`` tab in
    the report configuration form.

**Bugfixes**

- Fix access error when previewing or printing report. (`#415 <https://github.com/OCA/mis-builder/issues/415>`_)


15.0.4.0.5 (2022-07-19)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Support users without timezone. (`#388 <https://github.com/OCA/mis-builder/issues/388>`_)


15.0.4.0.4 (2022-07-19)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Allow deleting a report that has subreports. (`#431 <https://github.com/OCA/mis-builder/issues/431>`_)


15.0.4.0.2 (2022-02-16)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Fix access right issue when clicking the "Save" button on a MIS Report Instance form. (`#410 <https://github.com/OCA/mis-builder/issues/410>`_)


14.0.4.0.0 (2022-01-08)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- Remove various field size limits. (`#332 <https://github.com/OCA/mis-builder/issues/332>`_)


**Bugfixes**

- Support for the Odoo 13+ multi-company model. In multi-company mode, several allowed
  companies can be declared on MIS Report instances, and the report operates on the
  intersection of report companies and companies selected in the user context. (`#327 <https://github.com/OCA/mis-builder/issues/327>`_)
- The ``get_additional_query_filter`` argument of ``evaluate()`` is now propagated
  correctly. (`#375 <https://github.com/OCA/mis-builder/issues/375>`_)
- Use the ``parent_state`` field of ``account.move.line`` to filter entries in ``posted``
  and ``draft`` state only. Before, when reporting in draft mode, all entries were used
  (i.e. there was no filter), and that started including the cancelled entries/invoices in
  Odoo 13.+.

  This change also contains a **breaking change** in the internal API. For quite a while
  the ``target_move argument`` of AEP and other methods was not used by MIS Builder itself
  and was kept for backward compatibility. To avoid rippling effects of the necessary
  change to use ``parent_state``, we now remove this argument. (`#377 <https://github.com/OCA/mis-builder/issues/377>`_)


14.0.3.6.7 (2021-06-02)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- When on a MIS Report Instance, if you wanted to generate a new line of type comparison, you couldn't currently select any existing period to compare.
  This happened because the field domain was searching in a NewId context, thus not finding a correct period.
  Changing the domain and making it use a computed field with a search for the _origin record solves the problem. (`#361 <https://github.com/OCA/mis-builder/issues/361>`_)


14.0.3.6.6 (2021-04-23)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Fix drilldown action name when the account model has been customized. (`#350 <https://github.com/OCA/mis-builder/issues/350>`_)


14.0.3.6.5 (2021-04-23)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- While duplicating a MIS report instance, comparison columns are ignored because
  they would raise an error otherwise, as they keep the old source_cmpcol_from_id
  and source_cmpcol_to_id from the original record. (`#343 <https://github.com/OCA/mis-builder/issues/343>`_)


14.0.3.6.4 (2021-04-06)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- The drilldown action name displayed on the breadcrumb has been revised.
  The kpi description and the account ``display_name`` are shown instead
  of the kpi's technical definition. (`#304 <https://github.com/OCA/mis-builder/issues/304>`_)
- Add analytic group filters on report instance, periods and in the interactive
  view. (`#320 <https://github.com/OCA/mis-builder/issues/320>`_)


13.0.3.6.3 (2020-08-28)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Having a "Compare columns" added on a KPI with an associated style using a
  Factor/Divider did lead to the said factor being applied on the percentages
  when exporting to XLSX. (`#300 <https://github.com/OCA/mis-builder/issues/300>`_)


**Misc**

- `#280 <https://github.com/OCA/mis-builder/issues/280>`_, `#296 <https://github.com/OCA/mis-builder/issues/296>`_


13.0.3.6.2 (2020-04-22)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- The "Settings" button is now displayed for users with the "Show full accounting features" right when previewing a report. (`#281 <https://github.com/OCA/mis-builder/issues/281>`_)


13.0.3.6.1 (2020-04-22)
~~~~~~~~~~~~~~~~~~~~~~~

**Bugfixes**

- Fix ``TypeError: 'module' object is not iterable`` when using
  budgets by account. (`#276 <https://github.com/OCA/mis-builder/issues/276>`_)


13.0.3.6.0 (2020-03-28)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- Add column-level filters on analytic account and analytic tags.
  These filters are combined with a AND with the report-level filters
  and cannot be modified in the preview. (`#138 <https://github.com/OCA/mis-builder/issues/138>`_)
- Access to KPI from other reports in KPI expressions, aka subreports. In a
  report template, one can list named "subreports" (other report templates). When
  evaluating expressions, you can access KPI's of subreports with a dot-prefix
  notation. Example: you can define a MIS Report for a "Balance Sheet", and then
  have another MIS Report "Balance Sheet Ratios" that fetches KPI's from "Balance
  Sheet" to create new KPI's for the ratios (e.g. balance_sheet.current_assets /
  balance_sheet.total_assets). (`#155 <https://github.com/OCA/mis-builder/issues/155>`_)


13.0.3.5.0 (2020-01-??)
~~~~~~~~~~~~~~~~~~~~~~~

Migration to odoo 13.0.

12.0.3.5.0 (2019-10-26)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- The ``account_id`` field of the model selected in 'Move lines source'
  in the Period form can now be a Many2one
  relationship with any model that has a ``code`` field (not only with
  ``account.account`` model). To this end, the model to be used for Actuals
  move lines can be configured on the report template. It can be something else
  than move lines and the only constraint is that its ``account_id`` field
  has a ``code`` field. (`#149 <https://github.com/oca/mis-builder/issues/149>`_)
- Add ``source_aml_model_name`` field so extension modules providing
  alternative data sources can more easily customize their data source. (`#214 <https://github.com/oca/mis-builder/issues/214>`_)
- Support analytic tag filters in the backend view and preview widget.
  Selecting several tags in the filter means filtering on move lines which
  have *all* these tags set. This is to support the most common use case of
  using tags for different dimensions. The filter also makes a AND with the
  analytic account filter. (`#228 <https://github.com/oca/mis-builder/issues/228>`_)
- Display company in account details rows in multi-company mode. (`#242 <https://github.com/oca/mis-builder/issues/242>`_)


**Bugfixes**

- Propagate context to xlsx report, so the analytic account filter
  works when exporting to xslx too. This also requires a fix to
  ``report_xlsx`` (see https://github.com/OCA/reporting-engine/pull/259). (`#178 <https://github.com/oca/mis-builder/issues/178>`_)
- In columns of type Sum, preserve styles for KPIs that are not summable
  (eg percentage values). Before this fix, such cells were displayed without
  style. (`#219 <https://github.com/oca/mis-builder/issues/219>`_)
- In Excel export, keep the percentage point suffix (pp) instead of replacing it with %. (`#220 <https://github.com/oca/mis-builder/issues/220>`_)


12.0.3.4.0 (2019-07-09)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

- New year-to-date mode for defining periods. (`#165 <https://github.com/oca/mis-builder/issues/165>`_)
- Add support for move lines with negative debit or credit.
  Used by some for storno accounting. Not officially supported. (`#175 <https://github.com/oca/mis-builder/issues/175>`_)
- In Excel export, use a number format with thousands separator. The
  specific separator used depends on the Excel configuration (eg regional
  settings). (`#190 <https://github.com/oca/mis-builder/issues/190>`_)
- Add generation date/time at the end of the XLS export. (`#191 <https://github.com/oca/mis-builder/issues/191>`_)
- In presence of Sub KPIs, report more informative user errors when
  non-multi expressions yield tuples of incorrect lenght. (`#196 <https://github.com/oca/mis-builder/issues/196>`_)


**Bugfixes**

- Fix rendering of percentage types in Excel export. (`#192 <https://github.com/oca/mis-builder/issues/192>`_)


12.0.3.3.0 (2019-01-26)
~~~~~~~~~~~~~~~~~~~~~~~

**Features**

*Dynamic analytic filters in report preview are not yet available in 11,
this requires an update to the JS widget that proved difficult to implement
so far. Help welcome.*

- Analytic account filters. On a report, an analytic
  account can be selected for filtering. The filter will
  be applied to move lines queries. A filter box is also
  available in the widget to let the user select the analytic
  account during report preview. (`#15 <https://github.com/oca/mis-builder/issues/15>`_)
- Control visibility of analytic filter combo box in widget.
  This is useful to hide the analytic filters on reports where
  they do not make sense, such as balance sheet reports. (`#42 <https://github.com/oca/mis-builder/issues/42>`_)
- Display analytic filters in the header of exported pdf and xls. (`#44 <https://github.com/oca/mis-builder/issues/44>`_)
- Replace the last old gtk icons with fontawesome icons. (`#104 <https://github.com/oca/mis-builder/issues/104>`_)
- Use active_test=False in AEP queries.
  This is important for reports involving inactive taxes.
  This should not negatively effect existing reports, because
  an accounting report must take into account all existing move lines
  even if they reference objects such as taxes, journals, accounts types
  that have been deactivated since their creation. (`#107 <https://github.com/oca/mis-builder/issues/107>`_)
- int(), float() and round() support for AccountingNone. (`#108 <https://github.com/oca/mis-builder/issues/108>`_)
- Allow referencing subkpis by name by writing `kpi_x.subkpi_y` in expressions. (`#114 <https://github.com/oca/mis-builder/issues/114>`_)
- Add an option to control the display of the start/end dates in the
  column headers. It is disabled by default (this is a change compared
  to previous behaviour). (`#118 <https://github.com/oca/mis-builder/issues/118>`_)
- Add evaluate method to mis.report. This is a simplified
  method to evaluate kpis of a report over a time period,
  without creating a mis.report.instance. (`#123 <https://github.com/oca/mis-builder/issues/123>`_)

**Bugs**

- In the style form, hide the "Hide always" checkbox when "Hide always inherit"
  is checked, as for all other syle elements. (`#121 <https://github.com/OCA/mis-builder/pull/121>_`)

**Upgrading from 3.2 (breaking changes)**

If you use ``Actuals (alternative)`` data source in combination with analytic
filters, the underlying model must now have an ``analytic_account_id`` field.


11.0.3.2.2 (2018-06-30)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Fix bug in company_default_get call returning
  id instead of recordset
  (`#103 <https://github.com/OCA/mis-builder/pull/103>`_)
* [IMP] add "hide always" style property to make hidden KPI's
  (for KPI that serve as basis for other formulas, but do not
  need to be displayed).
  (`#46 <https://github.com/OCA/mis-builder/issues/46>`_)

11.0.3.2.1 (2018-05-29)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Missing comparison operator for AccountingNone
  leading to errors in pbal computations
  (`#93 <https://github.com/OCA/mis-builder/issue/93>`_)

10.0.3.2.0 (2018-05-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] make subkpi ordering deterministic
  (`#71 <https://github.com/OCA/mis-builder/issues/71>`_)
* [ADD] report instance level option to disable account expansion,
  enabling the creation of detailed templates while deferring the decision
  of rendering the details or not to the report instance
  (`#74 <https://github.com/OCA/mis-builder/issues/74>`_)
* [ADD] pbal and nbal accounting expressions, to sum positive
  and negative balances respectively (ie ignoring accounts with negative,
  resp positive balances)
  (`#86 <https://github.com/OCA/mis-builder/issues/86>`_)

11.0.3.1.2 (2018-02-04)
~~~~~~~~~~~~~~~~~~~~~~~

Migration to Odoo 11. No new feature.
(`#67 <https://github.com/OCA/mis-builder/pull/67>`_)

10.0.3.1.1 (2017-11-14)
~~~~~~~~~~~~~~~~~~~~~~~

New features:

* [ADD] month and year relative periods, easier to use than
  date ranges for the most common case.
  (`#2 <https://github.com/OCA/mis-builder/issues/2>`_)
* [ADD] multi-company consolidation support, with currency conversion
  (the conversion rate date is the end of the reporting period)
  (`#7 <https://github.com/OCA/mis-builder/issues/7>`_,
  `#3 <https://github.com/OCA/mis-builder/issues/3>`_)
* [ADD] provide ref, datetime, dateutil, time, user in the evaluation
  context of move line domains; among other things, this allows using
  references to xml ids (such as account types or tax tags) when
  querying move lines
  (`#26 <https://github.com/OCA/mis-builder/issues/26>`_).
* [ADD] extended account selectors: you can now select accounts using
  any domain on account.account, not only account codes
  ``balp[('account_type', '=', 'asset_receivable')]``
  (`#4 <https://github.com/OCA/mis-builder/issues/4>`_).
* [IMP] in the report instance configuration form, the filters are
  now grouped in a notebook page, this improves readability and
  extensibility
  (`#39 <https://github.com/OCA/mis-builder/issues/39>`_).

Bug fixes:

* [FIX] fix error when saving periods in comparison mode on newly
  created (not yet saved) report instances.
  `#50 <https://github.com/OCA/mis-builder/pull/50>`_
* [FIX] improve display of Base Date report instance view.
  `#51 <https://github.com/OCA/mis-builder/pull/51>`_

Upgrading from 3.0 (breaking changes):

* Alternative move line data sources must have a company_id field.

10.0.3.0.4 (2017-10-14)
~~~~~~~~~~~~~~~~~~~~~~~

Bug fix:

* [FIX] issue with initial balance rounding.
  `#30 <https://github.com/OCA/mis-builder/issues/30>`_

10.0.3.0.3 (2017-10-03)
~~~~~~~~~~~~~~~~~~~~~~~

Bug fix:

* [FIX] fix error saving KPI on newly created reports.
  `#18 <https://github.com/OCA/mis-builder/issues/18>`_

10.0.3.0.2 (2017-10-01)
~~~~~~~~~~~~~~~~~~~~~~~

New features:

* [ADD] Alternative move line source per report column.
  This makes mis buidler accounting expressions work on any model
  that has debit, credit, account_id and date fields. Provided you can
  expose, say, committed purchases, or your budget as a view with
  debit, credit and account_id, this opens up a lot of possibilities
* [ADD] Comparison column source (more flexible than the previous,
  now deprecated, comparison mechanism).
  CAVEAT: there is no automated migration to the new mechanism.
* [ADD] Sum column source, to create columns that add/subtract
  other columns.
* [ADD] mis.kpi.data abstract model as a basis for manual KPI values
  supporting automatic ajustment to the reporting time period (the basis
  for budget item, but could also server other purposes, such as manually
  entering some KPI values, such as number of employee)
* [ADD] mis_builder_budget module providing a new budget data source
* [ADD] new "hide empty" style property
* [IMP] new AEP method to get accounts involved in an expression
  (this is useful to find which KPI relate to a given P&L
  acount, to implement budget control)
* [IMP] many UI improvements
* [IMP] many code style improvements and some refactoring
* [IMP] add the column date_from, date_to in expression evaluation context,
  as well as time, datetime and dateutil modules

Main bug fixes:

* [FIX] deletion of templates and reports (cascade and retricts)
  (https://github.com/OCA/account-financial-reporting/issues/281)
* [FIX] copy of reports
  (https://github.com/OCA/account-financial-reporting/issues/282)
* [FIX] better error message when periods have wrong/missing dates
  (https://github.com/OCA/account-financial-reporting/issues/283)
* [FIX] xlsx export of string types KPI
  (https://github.com/OCA/account-financial-reporting/issues/285)
* [FIX] sorting of detail by account
* [FIX] computation bug in detail by account when multiple accounting
  expressions were used in a KPI
* [FIX] permission issue when adding report to dashboard with non admin user

10.0.2.0.3 (unreleased)
~~~~~~~~~~~~~~~~~~~~~~~

* [IMP] more robust behaviour in presence of missing expressions
* [FIX] indent style
* [FIX] local variable 'ctx' referenced before assignment when generating
  reports with no objects
* [IMP] use fontawesome icons
* [MIG] migrate to 10.0
* [FIX] unicode error when exporting to Excel
* [IMP] provide full access to mis builder style for group Adviser.

9.0.2.0.2 (2016-09-27)
~~~~~~~~~~~~~~~~~~~~~~

* [IMP] Add refresh button in mis report preview.
* [IMP] Widget code changes to allow to add fields in the widget more easily.

9.0.2.0.1 (2016-05-26)
~~~~~~~~~~~~~~~~~~~~~~

* [IMP] remove unused argument in declare_and_compute_period()
  for a cleaner API. This is a breaking API changing merged in
  urgency before it is used by other modules.

9.0.2.0.0 (2016-05-24)
~~~~~~~~~~~~~~~~~~~~~~

Part of the work for this release has been done at the Sorrento sprint
April 26-29, 2016. The rest (ie a major refactoring) has been done in
the weeks after.

* [IMP] hide button box in edit mode on the report instance settings form
* [FIX] Fix sum aggregation of non-stored fields
  (https://github.com/OCA/account-financial-reporting/issues/178)
* [IMP] There is now a default style at the report level
* [CHG] Number display properties (rounding, prefix, suffix, factor) are
  now defined in styles
* [CHG] Percentage difference are rounded to 1 digit instead of the kpi's
  rounding, as the KPI rounding does not make sense in this case
* [CHG] The divider suffix (k, M, etc) is not inserted automatically anymore
  because it is inconsistent when working with prefixes; you need to add it
  manually in the suffix
* [IMP] AccountingExpressionProcessor now supports 'balu' expressions
  to obtain the unallocated profit/loss of previous fiscal years;
  get_unallocated_pl is the corresponding convenience method
* [IMP] AccountingExpressionProcessor now has easy methods to obtain
  balances by account: get_balances_initial, get_balances_end,
  get_balances_variation
* [IMP] there is now an auto-expand feature to automatically display
  a detail by account for selected kpis
* [IMP] the kpi and period lists are now manipulated through forms instead
  of directly in the tree views
* [IMP] it is now possible to create a report through a wizard, such
  reports are deemed temporary and available through a "Last Reports Generated"
  menu, they are garbaged collected automatically, unless saved permanently,
  which can be done using a Save button
* [IMP] there is now a beginner mode to configure simple reports with
  only one period
* [IMP] it is now easier to configure periods with fixed start/end dates
* [IMP] the new sub-kpi mechanism allows the creation of columns
  with multiple values, or columns with different values
* [IMP] thanks to the new style model, the Excel export is now styled
* [IMP] a new style model is now used to centralize style configuration
* [FIX] use =like instead of like to search for accounts, because
  the % are added by the user in the expressions
* [FIX] Correctly compute the initial balance of income and expense account
  based on the start of the fiscal year
* [IMP] Support date ranges (from OCA/server-tools/date_range) as a more
  flexible alternative to fiscal periods
* v9 migration: fiscal periods are removed, account charts are removed,
  consolidation accounts have been removed

8.0.1.0.0 (2016-04-27)
~~~~~~~~~~~~~~~~~~~~~~

* The copy of a MIS Report Instance now copies period.
  https://github.com/OCA/account-financial-reporting/pull/181
* The copy of a MIS Report Template now copies KPIs and queries.
  https://github.com/OCA/account-financial-reporting/pull/177
* Usability: the default view for MIS Report instances is now the rendered preview,
  and the settings are accessible through a gear icon in the list view and
  a button in the preview.
  https://github.com/OCA/account-financial-reporting/pull/170
* Display blank cells instead of 0.0 when there is no data.
  https://github.com/OCA/account-financial-reporting/pull/169
* Usability: better layout of the MIS Report periods settings on small screens.
  https://github.com/OCA/account-financial-reporting/pull/167
* Include the download buttons inside the MIS Builder widget, and refactor
  the widget to open the door to analytic filtering in the previews.
  https://github.com/OCA/account-financial-reporting/pull/151
* Add KPI rendering prefixes (so you can print $ in front of the value).
  https://github.com/OCA/account-financial-reporting/pull/158
* Add hooks for analytic filtering.
  https://github.com/OCA/account-financial-reporting/pull/128
  https://github.com/OCA/account-financial-reporting/pull/131

8.0.0.2.0
~~~~~~~~~

Pre-history. Or rather, you need to look at the git log.
