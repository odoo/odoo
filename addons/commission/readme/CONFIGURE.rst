For adding commissions:

#. Go to *Commissions > Configuration > Commission types*.
#. Edit or create a new record.
#. Select a name for distinguishing that type.
#. Select the percentage type of the commission:

   * **Fixed percentage**: all commissions are computed with a fixed
     percentage. You can fill the percentage in the field "Fixed percentage".
   * **By sections**: percentage varies depending amount intervals. You can
     fill intervals and percentages in the section "Rate definition".

#. Select the base amount for computing the percentage:

   * **Sale/Invoice Amount**: percentage is computed from the amount put on
     sales order/invoice.
   * **Margin (Amount - Cost)**: percentage is computed from the profit only, taken the
     cost from the product.

For adding new agents:

#. Go to *Commissions > Agents*. You can also access from
   *Contacts > Contacts* or *Sales > Orders > Customers*.
#. Edit or create a new record.
#. On "Sales & Purchases" page, mark "Agent" check. It should be checked if
   you have accessed from first menu option.
#. There's a new page called "Agent information". In it, you can set following
   data:

   * The agent type, being in this base module "External agent" the only
     existing configuration. It can be extended with `hr_commission` module
     for setting an "Employee" agent type.
   * The associated commission type.
   * The settlement period, where you can select "Bi-weekly", "Monthly", "Quaterly",
     "Semi-annual" or "Annual".

   You will also be able to see the settlements that have been made to this
   agent from this page.
