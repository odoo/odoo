{
    "name": "Date Range",
    "version": "19.0.1.2.0",
    "category": "Hidden",
    "summary": "Named periods of time, reusable as a filter on any date field",
    "description": """
Date Range
==========

Define named periods — fiscal years, seasons, campaigns, tax declaration
periods — once, and reuse them anywhere a date or datetime field is filtered.
Where the web client's own date filters can only express calendar or rolling
intervals (this month, last 7 days, year to date), a date range is an arbitrary
span someone decided on: 15 February to 31 August, and it is called
"East valleys Spring - Summer".

Ranges are grouped by type. A type either allows its ranges to overlap or
requires them to be disjoint; when it requires them to be disjoint, PostgreSQL
enforces that through an exclusion constraint, so two sessions cannot create
colliding ranges at the same time.

A range may be nested inside a parent range of the same type. Overlap is then
checked between siblings only, so a sub-range is free to span its parent —
which is how a year is split into quarters without the quarters colliding with
the year.

Configuration
-------------
Settings > Technical > Date Ranges holds the types and the ranges. Recurring
periods are better produced by the *Generate Date Ranges* wizard than by hand;
a type can also carry generation defaults and be handed to the daily scheduled
action, which keeps its horizon topped up.

Usage
-----
Ranges show up in the backend domain editor: on a date or datetime field, the
operator list gains *in date range* plus one entry per type that has ranges,
and the value becomes a period selector instead of two date inputs.

To give a model a Period field in its search view, inherit the mixin::

    class AccountMove(models.Model):
        _name = "account.move"
        _inherit = ["account.move", "mixin.date.range.search"]

The mixin filters on the ``date`` field by default. Point it elsewhere with a
model attribute::

    _date_range_search_field = "invoice_date"
    """,
    "author": "ACSONE SA/NV, Odoo Community Association (OCA), AgroMarin",
    "website": "https://github.com/OCA/server-ux",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.access.csv",
        "data/ir_cron_data.xml",
        "views/date_range_type_views.xml",
        "views/date_range_views.xml",
        "wizards/date_range_generator.xml",
        "views/date_range_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "date_range/static/src/js/date_range_service.js",
            "date_range/static/src/js/date_range_provider.js",
            "date_range/static/src/js/domain_selector.esm.js",
        ],
        "web.assets_unit_tests": [
            "date_range/static/tests/**/*",
        ],
    },
}
