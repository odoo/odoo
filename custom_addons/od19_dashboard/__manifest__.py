{
    "name": "OD19 Dashboard Builder",
    "author": "OD19",
    "version": "19.0.3.0.0",
    "category": "Productivity",
    "summary": "Role-based dashboards with an in-browser drag & drop builder",
    "description": """
OD19 Dashboard Builder
======================
Delivers the role-based dashboard baseline (Owner / Management / Operational
Lead) defined in ``role-based-dashboard-blueprint.md`` and adds a web based
builder so each audience can customise and design its own dashboard.

Features
--------
* Pre-built Owner, Management and Operational dashboards matching the
  blueprint zones (summary, alerts, trend, detail).
* In-browser builder: add, edit, remove, drag to reorder and resize widgets.
* Widget types: KPI value (with period-over-period delta), bar, line, pie
  chart and list.
* KPI status rules are a reorderable first-match-wins table that compares the
  widget value with a constant, a goal, a percentage of the goal, another
  widget of the same dashboard, or a shifted period (previous, YtY, MtM, QtQ).
* Formula engine: 14 preset formulas (ratio, difference, growth, share, sum,
  average, weighted average, percent of goal, min, max, cumulative change, run
  rate, conversion rate, variance), a free-text expression evaluated through
  ``safe_eval``, and per-group evaluation on bar / line / pie charts.
* Live preview in the builder shows the resulting value and the number of
  records the widget would collect before the widget is saved.
* Reusable named formulas (``od19.dashboard.formula``) picked from the
  library and slotted per widget, including measures read across data sources.
* Conditional display (a widget hides itself when its condition is false) and
  alert messages carried by a status rule.
* Status rules are evaluated per chart bucket and per list row, so every bar,
  line point, pie slice and row is coloured by its own status.
* Data is read only from a curated whitelist of models and measures
  (``od19.dashboard.source``) so no arbitrary model can be queried.
""",
    "depends": [
        "web",
        "account",
        "sale_management",
        "purchase",
        "stock",
        "project",
        "mail",
        "spreadsheet_dashboard",
    ],
    "data": [
        "security/dashboard_security.xml",
        "security/ir.model.access.csv",
        "data/dashboard_source_data.xml",
        "data/dashboard_data.xml",
        "views/dashboard_views.xml",
        "views/dashboard_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_dashboard/static/src/dashboard/dashboard_action.js",
            "od19_dashboard/static/src/dashboard/builder_dialog.js",
            "od19_dashboard/static/src/dashboard/dashboard_action.xml",
            "od19_dashboard/static/src/dashboard/builder_dialog.xml",
            "od19_dashboard/static/src/dashboard/dashboard_action.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_dashboard/static/description/icon.svg",
}
