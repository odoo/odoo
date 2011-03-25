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
    "name":"Master Procurement Schedule",
    "version":"1.1",
    "author":["OpenERP SA",  "Grzegorz Grzelak (Cirrus)"],
    "category":"Warehouse",
    "images":["images/master_procurement_schedule.jpeg","images/sales_forecast.jpeg","images/stock_planning_line.jpeg","images/stock_sales_period.jpeg"],
    "depends":["hr","stock","sale"],
    "description": """
Purpose of MPS is to allow create a manual procurement apart of MRP scheduler (which works automatically on minimum stock rules).
=================================================================================================================================

This module is based on original OpenERP SA module stock_planning version 1.0 of the same name Master Procurement Schedule.
Terms used in the module:
- Stock and Sales Period - is the time (between Start Date and End Date) for which you plan Stock and Sales Forecast and make Procurement Planning.
- Stock and Sales Forecast - is the quantity of products you plan to sell in the Period.
- Stock Planning - is the quantity of products you plan to purchase or produce for the Period.

Because we have another module sale_forecast which uses terms "Sales Forecast" and "Planning" as amount values we will use terms "Stock and Sales Forecast" and "Stock Planning" to emphasize that we use quantity values.

Activity with this module is divided to three steps:
- Creating Periods. Mandatory step.
- Creating Sale Forecasts and entering quantities to them. Optional step but useful for further planning.
- Creating Planning lines, entering quantities to them and making Procurement. Making procurement is the final step for the Period.

Periods
-------
You have two menu items for Periods in "Sales Management - Configuration". There are:
- "Create Sales Periods" - Which automates creating daily, weekly or monthly periods.
- "Stock and sales Periods" - Which allows to create any type of periods, change the dates and change the State of period.

Creating periods is the first step you have to do to use modules features. You can create custom periods using "New" button in "Stock and Sales Periods" form or view but it is recommended to use automating tool.

Remarks:
- These periods (officially Stock and Sales Periods) are separated of Financial or other periods in the system.
- Periods are not assigned to companies (when you use multicompany feature at all). Module suppose that you use the same periods across companies. If you wish to use different periods for different companies define them as you wish (they can overlap). Later on in this text will be indications how to use such periods.
- When periods are created automatically their start and finish dates are with start hour 00:00:00 and end hour 23:59:00. when you create daily periods they will have start date 31.01.2010 00:00:00 and end date 31.01.2010 23:59:00. It works only in automatic creation of periods. When you create periods manually you have to take care about hours because you can have incorrect values form sales or stock.
- If you use overlapping periods for the same product, warehouse and company results can be unpredictable.
- If current date doesn't belong to any period or you have holes between periods results can be unpredictable.

Sales Forecasts
---------------
You have few menus for Sales forecast in "Sales Management - Sales Forecasts".
- "Create Sales Forecasts for Sales Periods" - which automates creating forecasts lines according to some parameters.
- "Sales Forecasts" - few menus for working with forecasts lists and forms.

Menu "Create Sales Forecasts for Sales Periods" creates Forecasts for products from selected Category, for selected Period and for selected Warehouse. It is an option "Copy Last Forecast" to copy forecast and other settings of period before this one to created one.

Remarks:
- This tool doesn't create lines, if relevant lines (for the same Product, Period, Warehouse and validated or created by you) already exists. If you wish to create another forecast, if relevant lines exists you have to do it manually using menus described bellow.
- When created lines are validated by someone else you can use this tool to create another lines for the same Period, Product and Warehouse.
- When you choose "Copy Last Forecast" created line takes quantity and some settings from your (validated by you or created by you if not validated yet) forecast which is for last period before period of created forecast. If there are few your forecasts for period before this one (it is possible) system takes one of them (no rule which of them).


Menus "Sales Forecasts"
On "Sales Forecast" form mainly you have to enter a forecast quantity in "Product Quantity". Further calculation can work for draft forecasts. But validation can save your data against any accidental changes. You can click "Validate" button but it is not mandatory.

Instead of forecast quantity you can enter amount of forecast sales in field "Product Amount". System will count quantity from amount according to Sale price of the Product.

All values on the form are expressed in unit of measure selected on form. You can select one of unit of measure from default category or from second category. When you change unit of measure the quanities will be recalculated according to new UoM: editable values (blue fields) immediately, non edited fields after clicking of "Calculate Planning" button.

To find proper value for Sale Forecast you can use "Sales History" table for this product. You have to enter parameters to the top and left of this table and system will count sale quantities according to these parameters. So you can select your department (at the top) then (to the left): last period, period before last and period year ago.

Remarks:


Procurement Planning
--------------------
Menu for Planning you can find in "Warehouse - Stock Planning".
- "Create Stock Planning Lines" - allows you to automate creating planning lines according to some parameters.
- "Master Procurement Scheduler" - is the most important menu of the module which allows to create procurement.

As Sales forecast is phase of planning sales. The Procurement Planning (Planning) is the phase of scheduling Purchasing or Producing. You can create Procurement Planning quickly using tool from menu "Create Stock Planning Lines", then you can review created planning and make procurement using menu "Master Procurement Schedule".

Menu "Create Stock Planning Lines" allows you to create quickly Planning lines for products from selected Category, for selected Period, and for selected Warehouse. When you check option "All Products with Forecast" system creates lines for all products having forecast for selected Period and Warehouse. Selected Category will be ignored in this case.

Under menu "Master Procurement Scheduler" you can generally change the values "Planned Out" and "Planned In" to observe the field "Stock Simulation" and decide if this value would be accurate for end of the Period.
"Planned Out" can be based on "Warehouse Forecast" which is the sum of all forecasts for Period and Warehouse. But your planning can be based on any other information you have. It is not necessary to have any forecast.
"Planned In" quantity is used to calculate field "Incoming Left" which is the quantity to be procured to make stock as indicated in "Stock Simulation" at the end of Period. You can compare "Stock Simulation" quantity to minimum stock rules visible on the form. But you can plan different quantity than in Minimum Stock Rules. Calculation is made for whole Warehouse by default. But if you want to see values for Stock location of calculated warehouse you can use check box "Stock Location Only".

If after few tries you decide that you found correct quantities for "Planned Out" and "Planned In" and you are satisfied with end of period stock calculated in "Stock Simulation" you can click "Procure Incoming Left" button to procure quantity of field "Incoming Left" into the Warehouse. System creates appropriate Procurement Order. You can decide if procurement will be made to Stock or Input location of calculated Warehouse.

If you don't want to Produce or Buy the product but just pick calculated quantity from another warehouse you can click "Supply from Another Warehouse" (instead of "Procure Incoming Left"). System creates pick list with move from selected source Warehouse to calculated Warehouse (as destination). You can also decide if this pick should be done from Stock or Output location of source warehouse. Destination location (Stock or Input) of destination warehouse will be used as set for "Procure Incoming Left".

To see proper quantities in fields "Confirmed In", "Confirmed Out", "Confirmed In Before", "Planned Out Before" and "Stock Simulation" you have to click button "Calculate Planning".

All values on the form are expressed in unit of measure selected on form. You can select one of unit of measure from default category or from second category. When you change unit of measure the quanities will be recalculated according to new UoM: editable values (blue fields) immediately, non edited fields after clicking of "Calculate Planning" button.

How Stock Simulation field is calculated:
Generally Stock Simulation shows the stock for end of the calculated period according to some planned or confirmed stock moves. Calculation always starts with quantity of real stock of beginning of current period. Then calculation adds or subtracts quantities of calculated period or periods before calculated.
When you are in the same period (current period is the same as calculated) Stock Simulation is calculated as follows:

Stock Simulation =
	Stock of beginning of current Period
	- Planned Out
	+ Planned In

When you calculate period next to current:

Stock Simulation =
	Stock of beginning of current Period
	- Planned Out of current Period
	+ Confirmed In of current Period  (incl. Already In)
	- Planned Out of calculated Period
	+ Planned In of calculated Period .

As you see calculated Period is taken the same way like in case above. But calculation of current Period are made a little bit different. First you should note that system takes for current Period only Confirmed In moves. It means that you have to make planning and procurement for current Period before this calculation (for Period next to current).

When you calculate Period ahead:

Stock Simulation =
	Stock of beginning of current Period
	- Sum of Planned Out of Periods before calculated
	+ Sum of Confirmed In of Periods before calculated (incl. Already In)
	- Planned Out of calculated Period
	+ Planned In of calculated Period.

Periods before calculated means periods starting from current till period before calculated.

Remarks:
- Remember to make planning for all periods before calculated because omitting these quantities and procurements can cause wrong suggestions for procurements few periods ahead.
- If you made planning few periods ahead and you find that real Confirmed Out is bigger than Planned Out in some periods before you can repeat Planning and make another procurement. You should do it in the same planning line. If you create another planning line the suggestions can be wrong.
- When you wish to work with different periods for some part of products define two kinds of periods (fe. Weekly and Monthly) and use them for different products. Example: If you use always Weekly periods for Products A, and Monthly periods for Products B your all calculations will work correctly. You can also use different kind of periods for the same products from different warehouse or companies. But you cannot use overlapping periods for the same product, warehouse and company because results can be unpredictable. The same apply to Forecasts lines.
""",
    "demo_xml":[],
    "update_xml": [
        "security/ir.model.access.csv",
        "stock_planning_view.xml",
        "wizard/stock_planning_create_periods_view.xml",
        "wizard/stock_planning_forecast_view.xml",
        "wizard/stock_planning_createlines_view.xml",
    ],
    "test": ["test/stock_planning.yml"],
    "active": False,
    "installable": True,
    "certificate" : "00872589676639788061",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

