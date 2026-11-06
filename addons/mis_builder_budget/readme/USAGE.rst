There are two ways to use this module: create budgets by KPI or budgets by
GL accounts. Currently, the two methods cannot be combined in the same budget.

**Budget by KPIs**

To use this this mode, you first need to flag at least some KPI in a MIS report
to be budgetable. You also need to configure the accumulation method on the KPI
according to their type.

The accumulation method determines how budgeted values spanning over a
time period are transformed to match the reporting period.

* Sum: values of shorter period are added, values of longest or partially overlapping
  periods are adjusted pro-rata temporis (eg monetary amount such as revenue).
* Average: values of included period are averaged with a pro-rata temporis weight.
  Typically used for values that do not accumulate over time (eg a number of employees).

When KPI are configured, you need to create a budget, using the MIS Budget (by
KPIs) menu, then click on the budget items button to create or import the
budgeted amounts for all your KPI and time periods.

**Budget by GL accounts**

You can also create budgets by GL accounts. In this case, the budget is
populated with one line per GL account (and optionally analytic account and/or
tags) and time period.

**Add budget columns to report instances**

Finally, a column (aka period) must be added to a MIS report instance,
selecting your newly created budget as a data source. The data will be adjusted
to the reporting period when displayed. Columns can be compared by adding a
column of type "comparison" or "sum".
