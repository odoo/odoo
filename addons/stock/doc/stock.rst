Stock Module
++++++++++++

This module can be applied for the simplest stock management case where you are only interested in knowing the quantity of each product in your stock as for a complex warehouse(s) management case, where for example each product gets a specific location in the stock and upon delivery it needs to be picked at a certain location and the products need to be packed in boxes and put on a pallet.  

Because of this huge difference in application, the main principles briefly will be explained first, whereafter we will dedicate one chapter on how to use the warehouse management in its simplest form.  From the third chapter on, we will explain every step in more detail, allowing you to discover the full potential of the module.  


1 Main principles explained briefly
***********************************

==================================================
Stock moves, locations, pickings and picking types
==================================================

A stock move is the elementary model in OpenERP that can move stock between 2 locations.  

In order to make it easy to move multiple products at once and pass that as an assignment to a warehouse operator, we use pickings that group these stock moves.  

We want to categorize the pickings in operation types.  As a warehouse manager you want to follow up the progress of the operations between the same (kind of) locations.  E.g. in the standard warehouse, not configuring anything, you will have 3 picking types: the incoming, internal and outgoing, but it is possible to create a picking type for all the packing operations that need to happen at the packing table.  The Warehouse > All Operations dashboard allows to see the progress of the pickings for each picking type.

You might have a weird feeling talking about moving from location A to location B, even for deliveries and incoming shipments.  That is because OpenERP uses a double-entry concept similar to double-entry accounting.  In OpenERP you do not talk of disappearance, consumption or loss of products: instead you speak only about stock moves from one place to another.

To satisfy the need for a counterpart to each stock movement, the software supports different types of stock locations:

* Physical stock locations,
* Partner locations (vendors and customers),
* Virtual locations as counterparts for production, inventory and scrap.

Partner locations represent your customers' and vendors' stocks. To reconcile them with your accounts, these stores play the role of third-party accounts. Receipt from a vendor can be shown by the movement of goods from a partner location to a physical location in your own company. As you see, vendor locations usually show negative stocks and customer locations usually show positive stocks.

Virtual locations as counterparts for production are used in manufacturing operations. Manufacturing is characterized by the consumption of raw materials and the production of finished products. Virtual locations are used for the counterparts of these two operations.

Inventory locations are counterparts of the stock operations that represent your company's profit and loss in terms of your stocks.

In Odoo, locations are structured hierarchically. You can structure your locations as a tree, dependent on a parent-child relationship. This gives you more detailed levels of analysis of your stock operations and the organization of your warehouses.



=========
Warehouse
=========

A warehouse represents the building where we stock our goods.  In case of multiple warehouses, you can enter the warehouse on your purchase orders and sale orders, such that your transporter knows where to deliver the goods or pick them up.   That is why a warehouse also has an address and a name.  

A warehouse corresponds also to a location.  As the locations are hierarchical, OpenERP will create one parent location for the warehouse that contains all the different locations in it.  

When you create a warehouse, the system will create the necessary operation types and main child locations for this main location in the background.


===========================================
MTO (Make to Order) and MTS (Make To Stock)
===========================================

A product can be MTO or MTS.  When a product is handled MTO, it means we will handle each order (e.g. sale order) individually and procure what is necessary, separately for every order.  When a product is handled MTS, we wait until there are sufficient orders and then we order everything at once taking into account a minimum stock (or a stock forecast) into account.  In OpenERP, we can automate minimum stock rules through reordering rules (or orderpoints) as shown in the next chapter. 

================
States of moves
================

* Draft
* Confirmed (Waiting Availability)
* Waiting (Waiting Another Move)
* Assigned (Available / Ready to Transfer)
* Done (Transferred)
* Cancel (Cancelled)

When we create a move, it will be in draft state.  It will have no influence on the virtual stock of the product.  It is only when we confirm the move that we make clear to the system that this move will be executed and should be taken into account for ordering new products.  The next state will however be different according to the scenario.  

For example, if the product is MTO and we have a delivery order from Stock to Customers, it will wait for a specific purchase order and will have the waiting (Waiting Another Move) state.  In case of an MTS product, the move will be configured as such that it will look for available stock in the source location itself and it will stay in the Confirmed (Waiting Availability) state.  

In these confirmed or waiting states it is possible to do "Check Availability".  If it can find the necessary stock, the state goes to Assigned.  In this state it is possible to effectively execute the move and transfer the products.  Incoming shipments are automatically available.  Effectively executing the move, brings it to the done state and makes it adapt the quantity available on hand.  

Normally, the picking associated to the move, will have the same state as it moves, but the picking can also have a partially available state.  It is possible that some products in the picking are available and some are not.  On a sales order or delivery order picking, you can specify if you want your customer to be delivered as soon as possible when only a part of the products is  available (partial delivery) or only all at once when everything is available (in order to save on transport costs for example).  So, if you can do a partial delivery, the picking state will be partially available when only some of the products are available (even a part of a move).

===================================================
Reordering rules, procurement and procurement group
===================================================

Procurements represent needs that need to be solved by a procurement rule.  For example, every sales order line will create a procurement in Customers.  This will be solved by a move for the delivery, which will, in case of a MTO product, create a new procurement (need) in Stock, which will be solved by a purchase order if it also has the buy-route.

It is not required however, to have this need in stock created by a move.  In case of MTS, the move will not create a procurement (need), but the procurement will originate from a reordering rule created for this product in stock.  

An reordering rule (= minimum stock rule) applies the following rule: if the virtual stock for the given location is lower than the minimum stock indicated in the rule, the system will automatically propose a procurement to increase the level of virtual stock to the maximum level given in the rule.  We underline that the rule is based on virtual quantities and not just on real quantities. It takes into account the calculation of orders and receipts to come.

You can also set multiple quantities in the minimum stock rules. If you set a multiple quantity of 3 the system will propose procurement of 15 pieces, and not the 13 it really needs. In this case, it automatically rounds the quantity upwards.

Pay attention to the fact that the maximum quantity is not the maximum you will have in stock. If we take the following situation: a company has 10 pieces of product with minimum stock rules defined for this product by Min quantity = 10, Max quantity = 30 and Qty multiple = 12. If an order of 2 pieces comes, a purchase of 24 pieces order will be executed. The first 22 pieces will be needed to have the correct quantity and the other 2 to have a multiple of 12. In the very end, the stock of this product will be equal to 32 pieces.

Scheduler: 

In order for the reordering rule to create the procurement, we need to launch the scheduler.  This can be done manually in Warehouse > Schedulers > Run Scheduler, but will normally be automated by a scheduled action.  (by default it is automated on a daily basis)

Procurement groups: 

Even when you have multiple lines in your sales order, you want one delivery order with all the lines of the sales order.  To accomplish this, Odoo groups the different procurements of this sale order into the same procurement group we create for the sales order.  That way, the moves of a delivery order stay together by putting moves of the same group in the same picking.

=================================
Consumables vs stockable products
=================================

Consumables will not be valued in the inventory valuation as they will have 0 value.  It is not possible to create reordering rules for consumables.  It is also not necessary to reserve stock for it as the move will go to the available state anyways.  


2 Standard configuration
************************

In this chapter, we want to show how to work with the simplest warehouse configuration.  (product MTO, product MTS with reordering rule, ...)

Suppose we have a little Apple Store.  The warehouse will be Apple Store and we manage only one location (no child locations).  We put a minimum stock of 10 iPad mini and 5 iPod nano.  We don't have stock for iBooks, but when a customer wants one, he can order one and will get it after a week.  

We will create a reordering rule for every product with minimum stock.  These orders could also be created by the point of sale.  The maximum of the orderpoint, we will take 15 and 10 and .  This orderpoint will need to be created in the Stock location.  


<<Show where we put vendor info>>
<<Show where we configure buy and mto>>
<<Show how to configure orderpoints>>

3 Beyond the magic of stock moves
*********************************

In the following chapters, we go a little deeper into the mechanisms behind the warehouse management.  In this chapter, we handle the stock moves.  Stock moves are not only the basic notions through which stock is moved, but can be chained and will determine their picking.  Chained moves are not only necessary in case of an MTO product, where the delivery waits for the specific incoming shipment, but for example also in multiple step in or out or when resupplying from other warehouses.  We will describe how pull and push rules are applied to created such chained moves.  

=================================
Assigning stock moves to pickings
=================================

When you want to give an assignment to a warehouse operator manually, you will create a picking and create the moves in it by specifying the different products and quantities.   When confirming a sale order however, Odoo will create procurements which will be solved bt creating moves.  First, these stock moves will be created without picking.  In a second step, they will be attributed to an existing picking or a picking will be created.

In order to assign the move to a picking, Odoo will check if the move was assigned an operation type (e.g. My Company: Delivery Orders) and if it does, it will search for a picking to assign the move to.  This picking should be in the correct state, picking type, procurement group (=group of procurements related to e.g. the same sale order) and source and destination locations.  If no picking can be found, it will create a new one.

This mechanism allows for a lot of flexibility when for example some products have to go through the Packing zone for packing and some don't.  That way, the packing order will still group the moves that need packing from the sale order and the direct moves will be grouped in a separate picking also.  For the delivery order, everything will be together in one picking again.  

A picking is almost entirely determined by the moves in it.  The state depends on the moves and the operation type, the source and destination location are those of the moves.  The scheduled date is calculated as a minimum date for the stock moves.

The state of a picking depends primarily on its moves: 

* If any move is draft, the picking is draft
* If all moves are done/cancel, the picking is done/cancel

The other states depend however also on the move type. The move type determines whether the customer expects to get all products of a picking at once (=all at once) or he wants it delivered to him as fast as possible. (=partial)  This move type can be determined manually, or can e.g. come from a sale order where it will be passed through the procurement group.  

In case of partial, a special state exists: partial availability.  It is possible that a move is in the confirmed / waiting state, but has partially some stock reserved.  This move will still be in the waiting/confirmed state, but have a flag partially available.  In that case, the picking will not stay in the confirmed/waiting state but go to the partially available state, which makes it possible to deliver the goods partially.  A picking is also partially available when some moves are assigned and others have no stock at all reserved.  

Sometimes a move does not have an operation type.  This means it will not be assigned to a picking.  This is the case for inventory corrections and moves in and out of production.


================================================================
Procurement (=pull) rules and push rules to create chained moves
================================================================

Push rules:

A rule that triggers another stock move based on the destination location of the original move.  The new move has as source location the destination location of the original move.  

Example: When products arrive manually in the “Input” location, you want to move them to “Stock” with a push rule afterwards.  

So, when a stock move “Vendor → Input” is confirmed, this rule will create another stock move: “Input → Stock”. It allows for 3 modes: automatic (the second operation will be validated automatically), manual (the second operation must be validated manually), manual no step added. (the destination of the first move is replaced instead of creating another stock move.

Push rules should typically only be used on incoming side when a purchase order is created manually and the goods need to be transferred to stock.  

Procurement (=pull) rules:

Pull rules are not the opposite of push rules! It’s very different as push rules impact moves and pull rules impact needs. (procurements)  It is actually better to call them procurement rules. It is however true that the push rules are applied on the destination location and pull rules on the source location.  

When a stock move is confirmed and its procurement method is 'Advanced: Apply procurement rules', it will create a procurement in the source location for the quantity of the move.  To fulfill this procurement, a procurement rule needs to be applied on this procurement.  There are several types of procurement rules with different results: move products from another location to the source location, purchase to the source location, produce towards the source location.  

A procurement does not need to be created by a stock move however.  A user can create a procurement manually and when we confirm a sale order, Odoo will create a procurement per sale order line in the Customers location.  Actually, this system of procurements, stock moves and procurement rules is used consistently throughout Odoo.  Even in the simplest warehouse configuration, when we run the procurements generated from the sale order, these procurement rules will generate the delivery order.

Procurements will pass through the following states when everything goes well:

- Confirmed: State when the procurement after the creation of the procurement
- Running: A procurement rule has been applied successfully (=> created a move or quotation or manufacturing order)
- Done: The procurement rule has been applied and the products have passed or are in the procurement's location

It is however possible that the procurement goes into Exception when no procurement rule can be found or when it is not possible to apply the rule (e.g. no vendor defined for the product).  When the products are no longer necessary, it is possible to Cancel the procurement.  

By default, the JIT scheduler is installed and the system will try to check the procurement immediately when it is confirmed.  If this would give performance issues, it is possible to uninstall this and then it will only run the procurements immediately generated by the sales order.  This will result in a delivery order, but the procurements generated by the stock moves in the delivery order, will not be run.  This will however be done by the Scheduler.  

A push rule can not be applied anymore when the rule was created from a pull rule, so pull rules kind of have priority over the push rules.  


=======================================================
Procurement method of stock moves and procurement rules
=======================================================

Whether a confirmed stock move created a procurement in the source location and applied the procurement rules, depends on its procurement method.  It has to be 'Apply procurement rules'

When a user creates a stock move in a picking, the stock move will have its procurement method 'Default: Take from stock'.  This means it will not create a procurement in the source location created to the move and will try to find the products in the available stock of the source location.  This is also the most logical thing to do when some goods need to be transferred internally for example to move death stock to the back of the warehouse.  

If the user chooses however to change the procurement method to 'Apply procurement rules', a procurement will be created in the source location.  And for example, creating a delivery order could lead in the simplest case (with purchase) to creating a purchase order the delivery order will be waiting for.

When you have procurement rules in a Pick > Pack > Ship configuration, it might be interesting to apply the procurement rules as it will generate the moves from stock to pack when you create a delivery order.  That way you can send something from the stock manually and still go through the pick/pack steps.

The procurement method is also only interesting for internal or outgoing pickings.  Incoming shipments do not need to reserve stock, so they are always 'Take from stock'.


Maybe you wonder how it is possible to create chains of more than two moves this way.  When a procurement rule creates another move, it can determine the procurement method of the new move.  In other words, it can determine if the new move will again look for procurement rules or will take from the stock.  

This makes it possible to create long chains.  For example, an MTS product with pick pack ship, will start with the confirmation of a sales order.  This will create a procurement, which will create a move from Output to Customers with procurement method "Apply procurement rules".  This will create procurement in Output.  This will continue like this until the procurement in Pack creates a stock move, which will have "Take from stock" instead.

<< Illustrate one from the chains from the Google Doc or the presentation of 2014 Open Days (see slideshare.net) shows this (and also how it is configured using routes)



========================
Chained Moves and States
========================

It is clear that the push and procurement rules allow to create long chain of moves.  When we talk about the chaining of moves we distinguish for a move between: 

* Destination move: The next move in the chain starting in the destination location of this move
* Original moves: The previous move(s) in the chain all arriving in the source location

When a move has original moves, it can only reserve stock that passed the original moves.  This is also why the state for these moves will go to Waiting Another Move instead of Waiting Availability.  

A move can only have one destination move, but multiple orginal moves.  Suppose you have two moves that are chained.  When the first one is split, the second one has 2 original moves and both moves have the same destination move.  

If the second one is split however, the split move, won't have any original moves on itself, but will check if it has not been split from a move with original moves, and might as such also take the Waiting for Another Move state.  


========================================================
Applied to MTO and MTS products and sale order and dates
========================================================

The checkbox MTO in the product form is actually a procurement rule that may be applied.  This means that the delivery order from stock will be created with procurement method "Apply procurement rules" instead of "Take from stock".


Lead times

All procurement operations (that is, the requirement for both production orders and purchase orders) are automatically calculated by the scheduler. But more than just creating each order, Odoo plans the timing of each step. A planned date calculated by the system can be found on each order document.

To organize the whole chain of manufacturing and procurement, Odoo bases everything on the delivery date promised to the customer. This is given by the date of the confirmation in the order and the lead times shown in each product line of the order. This lead time is itself proposed automatically in the field Customer Lead Time shown in the product form. This Customer Lead Time is the difference between the time on an order and that of the delivery.  There is also the sale_order_dates module that can help to promise a date to a customer.  Below is a calculation from the OpenERP books.

To see a calculation of the lead times, take the example of the cabinet above. Suppose that the cabinet is assembled in two steps, using the two following bills of materials.

Bill of Materials for 1 SHE100 Unit


+--------------+----------+-----------+
| Product Code | Quantity | UoM       |
+==============+==========+===========+
| SIDEPAN      |        2 | PCE       |
+--------------+----------+-----------+
| LIN040       |        1 | M         |
+--------------+----------+-----------+
| WOOD010      |    0.249 | M         |
+--------------+----------+-----------+
| METC000      |       12 | PCE       |
+--------------+----------+-----------+

Bill of Materials for 2 SIDEPAN Units


+--------------+----------+-----------+
| Product Code | Quantity | UoM       |
+==============+==========+===========+
| WOOD002      |     0.17 | M         |
+--------------+----------+-----------+

The SIDEPAN is made from an order using the workflow shown. The WOOD002 is purchased on order and the other products are all found in stock. An order for the product SHE100 will then generate two production orders (SHE100 and SIDEPAN) then produce two purchase orders for the product WOOD002. Product WOOD002 is used in the production of both SHE100 and SIDEPAN. Set the lead times on the product forms to the following:

+--------------+--------------------+-------------------------+--------------------+
| Product Code | Customer Lead Time | Manufacturing Lead Time | Vendor Lead Time   |
+=============+=====================+=========================+====================+
| SHE100       | 30 days            | 5 days                  |                    |
+--------------+--------------------+-------------------------+--------------------+
| SIDEPAN      |                    | 10 days                 |                    |
+--------------+--------------------+-------------------------+--------------------+
| WOOD002      |                    |                         | 5 days             |
+--------------+--------------------+-------------------------+--------------------+

A customer order placed on the 1st January will set up the following operations and lead times:

Delivery SHE100: 31 January (=1st January + 30 days),

Manufacture SHE100: 26 January (=31 January – 5 days),

Manufacture SIDEPAN: 16 January (=26 January – 10 days),

Purchase WOOD002 (for SHE100): 21 January (=26 January – 5 days),

Purchase WOOD002 (for SIDEPAN): 11 January (=16 January – 5 days).

In this example, OpenERP will propose placing two orders with the vendor of product WOOD002. Each of these orders can be for a different planned date. Before confirming these orders, the purchasing manager could group (merge) these orders into a single order.

Security Days

The scheduler will plan all operations as a function of the time configured on the products. But it is also possible to configure these factors in the company. These factors are then global to the company, whatever the product concerned may be. In the description of the company, on the Configuration tab, you find the following parameters:

Scheduler Range Days: all the procurement requests that are not between today and today plus the number of days specified here are not taken into account by the scheduler.

Manufacturing Lead Time: number of additional days needed for manufacturing,

Purchase Lead Time: additional days to include for all purchase orders with this vendor,

Security Days: number of days to deduct from a system order to cope with any problems of procurement, 


It is important to make a difference between production orders and purchase orders that are chained until the sale order (MTO) or when the chain is interrupted somewhere by an orderpoint.  When the scheduler creates the procurement of an orderpoint, the date is again today, so orders for an orderpoint need to be delivered faster, than in case of an MTO. 



4 Complex logistic flows
************************

In order to use the logistic flows to its fullest, you should activate the Advanced routes in Settings > Warehouse.

In the previous chapter, we talked about procurement rules and how they were applied.  We have not talked yet about when these procurement rules can be applied and how to configure them.  

A lot of Warehouses have input docks and output docks or have a packing zone where people want to repack the packages for the customer.  This can become quite complex and in order to manage this better, we group procurement rules and push rules into routes before having them applied to product, product categories, warehouses, ...  

Using these routes is simple as you just need to select them on e.g. a product or product category, but configuring them correctly is a little more difficult.  This is the reason why OpenERP will create the necessary routes automatically when you create a new warehouse.  Configuring the warehouse can then be a simple as choosing two step incoming and 3 step delivery, will always be supplied from warehouse B, will be purchased, ...

We will however explain the routes as you might maybe enhance the basic config from Odoo.

======
Routes
======

A Route is a collection of procurement rules and push rules.  Routes can be applied on:

* Product
* Product Category
* Warehouse
* Sale Order Line (activated through setting Settings > Configuration > Sales > Choose MTO, Dropship, ... on sale order lines)

On the route itself you can specify if you let the user change it on one of the above models.  For example, MTO and buy routes will simply be configured on the product level and then the user can choose the routes he want in the product form.  



===============================================================================
How does the system choose the correct procurement rule
===============================================================================

When a sales order creates a procurement it passes some useful information to it.  First, a sales order has a warehouse where the goods need to be picked up.  This warehouse will be copied on the procurement.  For example, when you have a procurement in Customers, but you know it has to be delivered from Warehouse WH, it can add a route with a procurement rule from WH/Stock to Customers and it will not apply a procurement rule from WH2/Stock to Customers.  Second, it is possible to supply an extra route on the sale order line itself.  This can come in handy when you decide on the sale order what route to follow e.g. if you sometimes decide to do dropshipping, you could enter it there.  These routes are copied on the procurement related to the sale order line.  

These routes on the procurement itself can also come in handy when the procurement can not find a suitable rule.  By adding a route, you can solve the procurement according to the situation.  (e.g. a certain product needs to be manufactured sometimes or bought sometimes) 

When Odoo needs to find a procurement/push rule, it will check the routes that can be applied to the procurement as follows:

* It will try to find a rule from the route(s) on the procurement first
* If it does not find any, it will try to find a rule from the route(s) on the product and product category (+ its parents)
* If it does not find any there, it will try to find a rule from the route(s) on the warehouse

If in any of these cases, multiple rules are found, it will select the rule with the highest priority.  This sequence can be changed in Warehouse > Routes (drag/drop the lines).  Normally, this will play almost no role as configuring this way makes it really complex.

Actually, when you select MTO on a product, this is a route that is chosen.  As in the basic configuration, it is defined on the product. (it is shown in the product form in a special widget that shows all the possible elements it could have in the one2many and you can select them)  As such, this route will be chosen over the standard route and will have a rule that puts procure method "Create Procurement on Source" to stock. In the route MTO all such rules for all warehouses will be put in the standard configuration.  

The reason behind such a configuration is that in most situations, the routes followed through the warehouse are the same for almost all products.  The exceptions on it can be defined for certain product categories or products.  Some things like MTO or buy/manufacture might be better to put on product level.  And then it is still possible that you change your mind on the sales order line.  

For the inter-warehouse configurations, there is also a possibility to put a warehouse on a procurement rule.  These rules will only be applied if the warehouse on the procurement is the same.


================================================
How does the system choose the correct push rule
================================================

Searching for a push rule is quite similar as for the pull rule.  It will however just search for the routes in the product and product category, then on those of the warehouse passed to the move or of the operation type of the move and then it will search a rule that is not in a route.


=======================
Simple Warehouse config
=======================

When you activate setting <<Advanced routes>> and go to Warehouse > Warehouse and select a Warehouse (or create a new), you will have a simplified way to configure these routes without worrying about its complexity.  

For the incoming and outgoing shipments, you can supply how many steps are needed to receive or ship goods.  This allows you e.g. to receive at the docks, and move the goods later on into a precise location in your racks.  It can also be interesting to do some quality control.  For shipping, you can also put your products at the gates first, but you might also want to package them at a separate location before bringing them at the gates. These routes will be directly related to the warehouse.  

If you check Purchase or Manufacture to resupply this warehouse, if a product is manufacture/buy, it will also be able to buy/manufacture from/in this warehouse. 

When you put a Default Resupply Warehouse, goods will always be supplied from this other Warehouse.  

You can choose multiple resupply warehouses.  These are selectable on the product / product category.  This is used when some products are supplied from one warehouse and others from another.  


===========================================
What happens behind simple warehouse config
===========================================

The wizard will create all the necessary locations and operation types to support the selected settings.

The Incoming shipments and Outgoing shipments routes are bundled into routes that are on the warehouse.  So, if you choose that warehouse, it will choose the route by default.  The incoming routes will also have the push rules associated with them.  

The purchase to resupply is a procurement rule added to the buy route, which will also buy to this warehouse.   

Also crossdock is added as a route to the warehouse.  This can be added on specific products and product categories that upon arrival are almost immediately transferred to the customer.  (might be mostly the case with mto products)



5 Reservation of stock and doing pack operations
************************************************

===========================================
Quants, reservations and removal strategies
===========================================

When the state of a move needs to pass from confirmed/waiting to assigned and the move is not an incoming shipment, the necessary stock (=quants) needs to be reserved.  

We need to consider the following when reserving stock:

* If there are original moves, the stock has to come from these moves
* If there are no original moves, it can take from the source location, but only if this stock has not been reserved on other moves.  If the user would want to take from other moves, he can unreserve those.  
* Also in case of returned moves, the system will check if the stock was moved by the move it was returned from. 
* When choosing the stock, we need to take into account the removal strategy.  

The removal strategy determines the order which stock gets reserved first.  By default the removal strategy is FIFO (First In First Out).  

A different removal strategy can be defined by product category and location.  For example, for a certain category of products LIFO (Last In First Out) could be chosen when taking products from its stock location.  

Quants are a technical object defining the actual stock.  If you have for example 70 pieces of product A in location A, you can have one quant of 70 pieces, but it is also possible to have several quants where the quantities sum to 70.  This way it is easy for the system to reserve stock, by reserving the quants.  If it does not need the whole quant, it can be split. 

==================
Packages and lots
==================

Products can be put in a package and a package can be put in another package.  The same hierarchical system is used as is the case for the locations.  When pack A is put in pack B, its full name becomes PACK B / PACK A.  

Lots are always linked to a certain product and can be put as being required depending on the incoming/outgoing/full traceability selected on the product. If a warehouse operator selects no lot (which you can only do if traceability is disabled), it can take any lot or without lot.  If he selects a lot, he has to take it.

In a picking, lots are defined on the pack operations and not on the moves.  This also means there is no virtual quantity of lots.  What is possible is reserving some lots and then you could see how much you have left of them.  (e.g. by looking in the Quants view which are reserved and which not)

=============================
Packaging and logistic units
=============================
Every package can have a packaging and a logistic unit.  The logistic unit determines the package itself e.g. it is a box 20x20x40 cm.  It is possible to put different products into the package. 

A packaging is however related to one product and should be applied on homogeneous packages (with only one product).  It describes how the products are put on each other e.g. you can put 20 pieces in box 20x20x40cm and on pallet 0.80m x 1.20m you will have 3 layers of 24 boxes.  


=======================
Pack operations
=======================

In order to define the operations that can be proposed / executed by the bar code interface, we create / process pack operations.  The stock moves itself will tell nothing about (from) which package / (specific)location/lot to take, in which (specific) location / package to put the goods.  That is the job of the pack operations.  

This is the model used by the bar code interface.  There are actually 2 types of pack operation: 

* Take entire package
* Take products from a certain package or not in a package


=========================
Preparing pack operations
=========================

If a picking will be processed by the bar code scanner, Odoo will propose the pack operations that need to be executed.  If it is an incoming shipment, it will be based on the moves, otherwise it will use the stock that has been reserved already.

Before creating the actual pack operations, Odoo will group the moves or reserved stock (quants) by:

* Lot: lot of the quant or empty if from stock move
* Product: product of the quant or stock move
* Package: the package from the quant or empty if from stock move
* Source location: the location of the quant or the source location of the move
* Destination location: For that we need to apply the putaway strategies

The putway strategies are similar to the removal strategies, but determine for the original destination location a child location where the goods should be deposited (instead as for the source location).  By default, there is no putaway strategy defined on the destination location.  In that case, the goods will be deposited in the destination location of the move.  In the stock module, there is one putaway strategy: fixed location.  For each such strategy you can also specify the related location.  Of course, based on this, custom developments make it possible to implement the putaway strategy you want (as it is applied on all of the stock being moved at once).

For the reserved stock (which also means it is determined which pieces of stock), Odoo will try to find as many packages (and as high-level) as possible for which the stock is entirely reserved and the destination location is the same for every piece of stock.  That way, the operator knows he can simply move the package to the destination location, instead of having to open the box unnecessarily.

An example might illustrate this further:

Some pallets with product A and some mixed pallets with product A en B are placed at the gates and need to be moved to stock.  A picking proposes to move all products A and B to stock.  Product A has loc A as fixed location putaway strategy and product B has loc B as fixed location.  In the pack operations, OpenERP will make an operation by pack for all pallets with only product A all to the loc A.  For the mixed pallets, it won't be able to make one pack operation.  It will say: move the product A from the mixed pallet to loc A and move the product B from the mixed pallet to loc B.  


============
Unreserving
============
If we want to use a certain piece of stock on another picking instead of the picking selected, we can unreserve this piece of stock by clicking on the Unreserve button of the picking.  

It is however possible that during the pack operations, the warehouse operator has chosen the stock from another location.  In that case, other quants need to be reserved also.  When processing this picking further on, the system will unreserve the stock and do the reserve process again, taking into account the created pack operations from the bar code scanner interface.


===============================================
Bar code interface and checking pack operations
===============================================

A picking can be processed in the back-office interface by processing the moves, but then it will not be possible to do pack operations or change the locations.  

If you choose in "Enter Transfer details" in the picking, the system will prepare the pack operations and you will be guided to the bar code interface.  

Also in the Warehouse > All Operations, it is possible to change to the bar code interface and do all the pickings at once.  

When using the bar code interface, the pack operations will be prepared as explained above.  In the bar code interface it is then possible to change the prepared pack operations to the effective operations the warehouse operator executed.  

- The operator can filter the operations on product/pack/source location
- The operator should fill in the quantity on the filtered line.  He should type enter to confirm.  If the quantity is correct, the line will become green.  
- The operator might put the products in a new pack
- Afterwards, the operator can process the products and mark as done.  That way they will get into operations done, instead of todo.  
- The operator can also change source/destination location

- If everything has been done and the operator took the correct products, it will also finish the picking.  
If this is not the case, he can do "Create backorder", and then he needs to check if all the products have been done or not.  If only part has been done, OpenERP needs to create a backorder for it.  It is however more complicated than that.  The operator could have chosen other source/destination location or even create new pack operations with new products.  

In order to manage all these possible changes, in the background, Odoo is going to do a matching between the pack operations executed by the warehouse operator and the moves given as assignment beforehand.
It is also possible that the operator chooses other stock than was reserved at forehand.  In that case, Odoo will need to redo the reservation of the stock.

The matching of the pack operations and stock moves will determine if extra moves need to be created or if some moves need to go (partially) into backorder.  


6 Transferring
***************


=====================
Actual transferring
=====================

If there are no pack operations, it will process the move as such. (with only the information from the move)  

In case of pack operations: 

First it will check the matching between pack operations and moves and create the necessary extra moves or backorder.  After having split the moves and created the extra, it can be necessary to rereserve the quants and recompute the matching.  After having done that, it will process all the moves that need to be done.  It will look at the matchings between the move and the pack operations and take them into account.  That way it will take the correct quants from the pack operation and put it in the correct pack and destination location

======================
Negative stocks
======================

It is still possible that upon transferring for an internal shipment or delivery, the necessary quants or stock can not be found.  In that case, it will create negative stock (negative quants).    

When later on, a move brings in some goods that correspond to this negative stock, the quant can be reconciled with it.

Normally, chained moves have to take from their original moves.  Only when you do force assign a move with original moves it can also take from the regular stock that is not chained.  It will however not assign this stock before actually doing the transfer.  


7 Returns and cancellation
***************************

========================
Returns
========================

It is possible to create a return on a done picking.  This wizard will propose to return everything that is still in the destination location.  If it can't find stock from the original move, it will create negative quants.  


======================
Cancellation
======================

When you cancel a procurement, it will cancel everything in the backwards direction. When you cancel a move itself, it will cancel in the forward direction. 

This will happen only if the move has the attribute 'Propagate Cancel and Split' set to true.  Also, when a procurement rule (or a push rule) is applied to create another move, it will copy its 'Propagate Cancel and Split' on the move.  On the procurement rules, it is actually true by default.  This also works for the purchase orders.

=============================
Procurement group propagation
=============================
A procurement group can be fixed on a rule, can be propagated (default = propagate) or can be none.  The advantage of putting a fixed procurement group on the rule is that you could for example put all the orders for your picking in one giant picking.  That way, you take all the orders to the picking table and over there you could do the individual pickings for every customer.

A procurement group can be put on a reordering rule also, which will put it on the generated procurement.

This is not something which is propagated to the purchase / manufacturing order.


8 Inventory
***********

When you start using Odoo, you might have an inventory to start from.  (Starting Inventory)  You will enter all the products that are in the warehouse and Odoo will put them in this position.  When you validate this inventory, Odoo will create the necessary stock moves that will go from Inventory Loss to these locations.

It is possible that operations in the warehouse are not well registered and the stock in Odoo does not correspond exactly to the physical stock in the warehouse.  Of course, you do not want this to happen, but errors do happen and a way to solve these mistakes, is to check the inventory once and a while.  Most companies will do an entire inventory yearly.

You can decide to do a certain product or a certain location.  So, you are not required to do all the inventory at once.  In a next step Odoo will propose all the current stock in the system.  When you correct this stock, Odoo will create the necessary moves in a second tab.  The inventory is done, when these moves are all transferred.



9 Use case: Small distribution Centre for a Warehouse Chain AllStore
********************************************************************

A use case can make a lot of concepts real. That is also why it might be interesting to think a while or to try to solve it yourself before reading the solution after the description of the use case.  

===========
Description
===========

AllStore wants to implement a small warehouse for 5 nearby shops.  These shops will be using the Point of Sale.  1 shop is rather big, the 4 others are really small.  Everyday a truck will go to the 5 shops as the fresh products need to be delivered every day.  Also a separate compartment in the truck is foreseen for the frozen products.  

In the warehouse itself, we have docks for Input and Output.  The fresh goods will be crossdocked as much as possible as they will arrive early in the morning from the vendor and will then be processed and transferred to the stores on the same day.  

The frozen goods will be received at the docks, but not far from the fresh products as it is a little colder over there.  Once processed, they will go into the freezer, where they will be taken from their pallets.  

The frozen and fresh goods will be delivered from the vendor.  The frozen goods have a lot and expiry date on their individual packages and we won't enter them in the system as they expire that fast, but for the fresh goods, we need to supply the dates.  

There also a lot of dry products, that are sometimes bought from a vendor and will sometimes arrive weekly from a truck from the main warehouse of AllStore.  

For outbound, the dry products will be packaged before being shipped.  Also the frozen goods need to be picked for that.  The consolidation zone for frozen goods is however different than that for the normal dry goods.  

The distribution centre is also used as a manufacturing plant for coffee.  The coffee will be supplied to the main warehouse and the material necessary will come from the stock.  The production manager will input the necessary production orders when necessary.  For every manufacturing order a separate order will be made for the raw coffee, but some secret ingredients will come from stock.  It is important to know which coffee is made from which lots.  



========
Solution
========

As modules, it is clear we need stock, point of sale, purchase, sale and manufacturing.  For the settings for the warehouse, we want to use multiple locations and advanced routes.  We also need packages, lots and expiry dates on those lots.  It is also in handy to see the UoMs as Apples and Pears will be measured by kg instead of by unit.  

When we want to configure this in OpenERP, we will typically start by configuring the warehouses.  The logic for choosing the routes in OpenERP, is to first check those of the warehouse and then those of the product and product categories.  So, the logic for configuring, is to put the generic routes on the warehouses and to put exceptions on these general rules on product and product categories.  

The default “My Company” warehouse can be the main warehouse.  We skip this configuration as it is not our goal.  The only thing we know is that the coffee might be supplied from our distribution centre. 
 
Then we configure the “Distribution Centre”.  As products always pass through the docks, by default it will be two step input and 3-step output (pick-pack-ship).  Dry products will follow this simple flow.  

We will also manufacture and purchase in this warehouse.  (Will only be done when it is configured on the product, even if we check the checkbox).  We will not supply a default resupply warehouse as it might be bought, but the main warehouse will be one of the supply warehouses.  

The shops can be created by using single step incoming/ outgoing  and each time the Distribution Centre as default resupply warehouse as the goods are always delivered to the shop from the Distribution Centre.  2-step incoming might be in handy for the bigger shop as it can be in handy to scan the goods upon arrival before putting everything into the store itself.  

As fresh products are always crossdocked, we can create a category with fresh products and put the CrossDock route on it which was created.  This crossdock route, created by default, will always apply the procurement rules..  

As it is not logical to run between the freezers and the dry products, their stocks should be separated and should be handled by different pull flows.  Frozen goods and dry products should be on different pickings when handled inside the warehouse.  (not for shipping)

This means we will need to alter the routes and locations and provide 2 extra product categories (Frozen and Dry).  We can start by creating two child locations of Stock: Stock / Freezer and Stock /  Dry.  For the warehouse DC, 2 routes were created that need to be changed: 2 step inbound and 3-step pick pack ship.  We can duplicate those two routes for the frozen.  In the 4 routes we need to change the stock location to the stock/Freezer or stock/Dry accordingly.  

On the product category Frozen Goods we will need to put the two duplicated routes.  That way, only the frozen goods will be sent to the freezer.  

For the manufacturing of the coffee, production orders will be created manually upon need in dry stock, but the raw coffee beans as raw materials will 'apply the procurement rules' and need the MTO route.  The secret ingredients will be taken from the stock.  We should not forget to create a BoM for the Coffee with the Raw Coffee Beans and the Secret Ingredients in it.  

As the routes have been configured, we can create products.  As the products will be handled by the PoS in the shops, it would be nice if at least some of them can have minimum stock rules in order to replenish them there.  So we need to define reordering rules (= minimum stock rules) for these products in the Shop1 / Stock location and Shop2 / Stock location.  For the fresh products, this is all we need to do as they will be crossdocked in the Distribution Centre and this will work MTO.  For the frozen and dry products, we need to define an orderpoint in the stock of the Distribution Centre also.  Take care that the orderpoint is defined in DC/Stock/Freezer and not DC/Stock for example.  No rule will be found in Stock.  

Putaway strategies can be interesting in order to find back our products easier and to give them a fixed location.  For example we can create a sub-category Stock / Freezer / Freezer A with a putaway strategy in Stock / Freezer with fixed location Freezer A.  

For the fresh products, we need to supply a lot.  This can be done by selecting “Track All Lots” on the product form.  

By default, products will have the buy route, but if they get resupplied from the main warehouse, it is possible to change on the product form.  Suppose even that you don't know for certain products as both strategies are possible.  So, if you uncheck buy, no route is active on the product form, the procurement will go into exception.  Then you can put the right route (buy or supply from main warehouse) as preferred route on the procurement.  

































