In order to create an Excel report you can define a report of type 'xlsx' in a static or dynamic way:

* Static syntax: cf. ``account_move_line_report_xls`` for an example.
* Dynamic syntax: cf. ``report_xlsx_helper_demo`` for an example

The ``AbstractReportXlsx`` class contains a number of attributes and methods to
facilitate the creation excel reports in Odoo.

* Cell types

  string, number, boolean, datetime.

* Cell formats

  The predefined cell formats result in a consistent
  look and feel of the Odoo Excel reports.

* Cell formulas

  Cell formulas can be easily added with the help of the ``_rowcol_to_cell()`` method.

* Excel templates

  It is possible to define Excel templates which can be adapted
  by 'inherited' modules.
  Download the ``account_move_line_report_xls`` module
  from http://apps.odoo.com as example.

* Excel with multiple sheets

  Download the ``account_asset_management_xls`` module
  from http://apps.odoo.com as example.
