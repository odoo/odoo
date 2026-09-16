A typical extension is to provide a mechanism to filter reports on analytic dimensions
or operational units. To implement this, you can override _get_additional_move_line_filter
and _get_additional_filter to further filter move lines or queries based on a user
selection. A typical use case could be to add an analytic account field on mis.report.instance,
or even on mis.report.instance.period if you want different columns to show different
analytic accounts.
