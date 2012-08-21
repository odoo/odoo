# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Master Procurement Schedule",
    "version": "1.2",
    "author": "OpenERP SA and Grzegorz Grzelak (OpenGLOBE)",
    "category" : "Manufacturing",
    "images": ["images/master_procurement_schedule.jpeg","images/sales_forecast.jpeg","images/stock_planning_line.jpeg","images/stock_sales_period.jpeg"],
    "depends": ["crm", "stock","sale"],
    "description": """
MPS allows to create a manual procurement plan apart of the normal MRP scheduling, which works automatically based on minimum stock rules.
==========================================================================================================================================

Quick Glossary:
---------------
    - Stock Period - the time boundaries (between Start Date and End Date) for
      your Sales and Stock forecasts and planning
    - Sales Forecast - the quantity of products you plan to sell during the
      related Stock Period.
    - Stock Planning - the quantity of products you plan to purchase or produce
      for the related Stock Period.

To avoid confusion with the terms used by the ``sale_forecast`` module,
("Sales Forecast" and "Planning" are amounts) we use terms "Stock and Sales
Forecast" and "Stock Planning" to emphasize that we use quantity values.

Where to begin:
---------------
Using this module is done in three steps:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    * Create Stock Periods via the **Warehouse** > **Configuration** > **Stock Periods** menu
      (Mandatory step)
    * Create Sale Forecasts fill them with forecast quantities, via the
      **Sales** > **Sales Forecast** menu. (Optional step but useful for further planning)
    * Create the actual MPS plan, check the balance and trigger the procurements
      as required. The actual procurement is the final step for the Stock Period.

Stock Period configuration:
---------------------------
You have two menu items for Periods in "**Warehouse** > **Configuration** > **Stock Periods**".

There are:
~~~~~~~~~~
    * "Create Stock Periods" - can automatically creating daily, weekly or
      monthly periods.
    * "Stock Periods" - allows to create any type of periods, change the dates
      and change the state of period.

Creating periods is the first step. You can create custom periods using the "New"
button in "Stock Periods", but it is recommended to use the automatic assistant
"Create Stock Periods".

Remarks:
++++++++
    - These periods (Stock Periods) are completely distinct from Financial or
      other periods in the system.
    - Periods are not assigned to companies (when you use multicompany). Module
      suppose that you use the same periods across companies. If you wish to use
      different periods for different companies define them as you wish (they can
      overlap). Later on in this text will be indications how to use such periods.
    - When periods are created automatically their start and finish dates are with
      start hour 00:00:00 and end hour 23:59:00. When you create daily periods they
      will have start date 31.01.2010 00:00:00 and end date 31.01.2010 23:59:00.
      It works only in automatic creation of periods. When you create periods
      manually you have to take care about hours because you can have incorrect
      values form sales or stock.
    - If you use overlapping periods for the same product, warehouse and company
      results can be unpredictable.
    - If current date doesn't belong to any period or you have holes between
      periods results can be unpredictable.

Sales Forecasts configuration:
------------------------------
You have few menus for Sales forecast in "**Sales** > **Sales Forecasts**":
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - "Create Sales Forecasts" - can automatically create forecast lines
      according to your needs
    - "Sales Forecasts" - for managing the Sales forecasts

Menu "Create Sales Forecasts" creates Forecasts for products from selected
Category, for selected Period and for selected Warehouse.
It is also possible to copy the previous forecast.

Remarks:
++++++++
    - This tool doesn't duplicate lines if you already have an entry for the same
      Product, Period, Warehouse, created or validated by the same user. If you
      wish to create another forecast, if relevant lines exists you have to do it
      manually as described below.
    - When created lines are validated by someone else you can use this tool to
      create another line for the same Period, Product and Warehouse.
    - When you choose "Copy Last Forecast", created line take quantity and other
      settings from your (validated by you or created by you if not validated yet)
      forecast which is for last period before period of created forecast.

On "Sales Forecast" form mainly you have to enter a forecast quantity in
"Product Quantity". Further calculation can work for draft forecasts. But
validation can save your data against any accidental changes. You can click
"Validate" button but it is not mandatory.

Instead of forecast quantity you may enter the amount of forecast sales via the
"Product Amount" field. The system will count quantity from amount according to
Sale price of the Product.

All values on the form are expressed in unit of measure selected on form. You can
select a unit of measure from the default category or from secondary category.
When you change unit of measure the forecast product quantity will be re-computed
according to new UoM.

To work out your Sale Forecast you can use the "Sales History" of the product.
You have to enter parameters to the top and left of this table and system will
count sale quantities according to these parameters. So you can get results for
a given sales team or period.


MPS or Procurement Planning:
----------------------------
An MPS planning consists in Stock Planning lines, used to analyze and possibly
drive the procurement of products for each relevant Stock Period and Warehouse.

The menu is located in "**Warehouse** > **Schedulers** > **Master Procurement Schedule**":
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - "Create Stock Planning Lines" - a wizard to help automatically create many
      planning lines
    - "Master Procurement Schedule" - management of your planning lines

Similarly to the way Sales forecast serves to define your sales planning, the MPS
lets you plan your procurements (Purchase/Manufacturing).You can quickly populate
the MPS with the "Create Stock Planning Lines" wizard, and then proceed to review
them via the "Master Procurement Schedule" menu.

The "Create Stock Planning Lines" wizard lets you to quickly create all MPS lines
for a given Product Category, and a given Period and Warehouse.When you enable
the "All Products with Forecast" option of the wizard, the system creates lines
for all products having sales forecast for selected Period and Warehouse (the
selected Category will be ignored in this case).

Under menu "Master Procurement Schedule" you will usually change the "Planned Out"
and "Planned In" quantities and observe the resulting "Stock Simulation" value
to decide if you need to procure more products for the given Period. "Planned Out"
will be initially based on "Warehouse Forecast" which is the sum of all outgoing
stock moves already planned for the Period and Warehouse. Of course you can alter
this value to provide your own quantities. It is not necessary to have any forecast.
"Planned In" quantity is used to calculate field "Incoming Left" which is the
quantity to be procured to reach the "Stock Simulation" at the end of Period. You
can compare "Stock Simulation" quantity to minimum stock rules visible on the form.
And you can plan different quantity than in Minimum Stock Rules. Calculations are
done for whole Warehouse by default, if you want to see values for Stock location
of calculated warehouse you can check "Stock Location Only".

When you are satisfied with the "Planned Out", "Planned In" and end of period
"Stock Simulation", you can click on "Procure Incoming Left" to create a
procurement for the "Incoming Left" quantity. You can decide if procurement will
go to the to Stock or Input location of the Warehouse.

If you don't want to Produce or Buy the product but just transfer the calculated
quantity from another warehouse you can click "Supply from Another Warehouse"
(instead of "Procure Incoming Left") and the system will create the appropriate
picking list (stock moves). You can choose to take the goods from the Stock or
the Output location of the source warehouse. Destination location (Stock or Input)
in the destination warehouse will be taken as for the procurement case.

To see update the quantities of "Confirmed In", "Confirmed Out", "Confirmed In
Before", "Planned Out Before" and "Stock Simulation" you can press "Calculate
Planning".

All values on the form are expressed in unit of measure selected on form. You can
select one of unit of measure from default category or from secondary category.
When you change unit of measure the editable quantities will be re-computed
according to new UoM. The others will be updated after pressing "Calculate Planning".

Computation of Stock Simulation quantities:
-------------------------------------------
The Stock Simulation value is the estimated stock quantity at the end of the
period. The calculation always starts with the real stock on hand at the beginning
of the current period, then adds or subtracts the computed quantities.

When you are in the same period (current period is the same as calculated) Stock Simulation is calculated as follows:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Stock Simulation =** Stock of beginning of current Period - Planned Out + Planned In

When you calculate period next to current:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Stock Simulation =** Stock of beginning of current Period - Planned Out of current Period + Confirmed In of current Period  (incl. Already In) - Planned Out of calculated Period + Planned In of calculated Period .

As you see the calculated Period is taken the same way as in previous case, but
the calculation in the current Period is a little bit different. First you should
note that system takes for only Confirmed moves for the current period. This means
that you should complete the planning and procurement of the current Period before
going to the next one.

When you plan for future Periods:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Stock Simulation =** Stock of beginning of current Period - Sum of Planned Out of Periods before calculated + Sum of Confirmed In of Periods before calculated (incl. Already In) - Planned Out of calculated Period + Planned In of calculated Period.

Here "Periods before calculated" designates all periods starting with the current
until the period before the one being calculated.

Remarks:
++++++++
    - Remember to make the proceed with the planning of each period in chronological
      order, otherwise the numbers will not reflect the reality
    - If you planned for future periods and find that real Confirmed Out is larger
      than Planned Out in some periods before, you can repeat Planning and make
      another procurement. You should do it in the same planning line. If you
      create another planning line the suggestions can be wrong.
    - When you wish to work with different periods for some products, define two
      kinds of periods (e.g. Weekly and Monthly) and use them for different
      products. Example: If you use always Weekly periods for Product A, and
      Monthly periods for Product B all calculations will work correctly. You
      can also use different kind of periods for the same product from different
      warehouse or companies. But you cannot use overlapping periods for the same
      product, warehouse and company because results can be unpredictable. The
      same applies to Forecasts lines.
""",
    "data": [
        "security/stock_planning_security.xml",
        "security/ir.model.access.csv",
        "stock_planning_view.xml",
        "wizard/stock_planning_create_periods_view.xml",
        "wizard/stock_planning_forecast_view.xml",
        "wizard/stock_planning_createlines_view.xml",
    ],
    "test": ["test/stock_planning.yml"],
    "auto_install": False,
    "installable": True,
    "certificate" : "00872589676639788061",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

