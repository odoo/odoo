Stock Module
++++++++++++

This module can be applied for the simplest case where you are only interested in knowing the quantity of each product in your stock as for a complex warehouse(s) management case, where for example each product gets a specific location in the stock and upon delivery it needs to be picked at a certain location and the products need to be packed in boxes and put on a pallet.  

Because of this huge difference in application, the main principles briefly will be explained first, whereafter we will dedicate one chapter on how to use the warehouse management in its simplest form.  From the third chapter on, we will explain every step in more detail, allowing you to discover the full potential of the module.  


1 Main principles explained briefly
***********************************

==================================================
Stock moves, locations, pickings and picking types
==================================================

A stock move is the elementary model in OpenERP that can move stock between 2 locations.  

In order to make it easy to move multiple products at once and pass that as an assignment to a warehouse operator, we use pickings that group these stock moves.  

We want to categorize the pickings in picking types.  As a warehouse manager you want to follow up the progress of the operations between the same (kind of) locations.  E.g. by default, in the default warehouse, you will have 3 picking types: the incoming, internal and outgoing, but it is possible to create a picking type for all the packing operations that need to happen at the packing table.  The Warehouse > All Operations dashboard allows to see the progress of the pickings for each picking type.  

You might have a weird feeling talking about moving from location A to location B, even for deliveries and incoming shipments.  That is because OpenERP uses a double-entry concept similar to double-entry accounting.  In OpenERP you do not talk of disappearance, consumption or loss of products: instead you speak only about stock moves from one place to another.

To satisfy the need for a counterpart to each stock movement, the software supports different types of stock locations:

* Physical stock locations,
* Partner locations (suppliers and customers),
* Virtual locations as counterparts for production, inventory and scrap.

Partner locations represent your customers' and suppliers' stocks. To reconcile them with your accounts, these stores play the role of third-party accounts. Reception from a supplier can be shown by the movement of goods from a partner location to a physical location in your own company. As you see, supplier locations usually show negative stocks and customer locations usually show positive stocks.

Virtual locations as counterparts for production are used in manufacturing operations. Manufacturing is characterized by the consumption of raw materials and the production of finished products. Virtual locations are used for the counterparts of these two operations.

Inventory locations are counterparts of the stock operations that represent your company's profit and loss in terms of your stocks.

In OpenERP, locations are structured hierarchically. You can structure your locations as a tree, dependent on a parent-child relationship. This gives you more detailed levels of analysis of your stock operations and the organization of your warehouses.



=========
Warehouse
=========

A warehouse represents the building where we stock our goods.  In case of multiple warehouses, you can enter the warehouse on your purchase orders and sale orders, such that your transporter knows where to deliver or pick it up.   That is why a warehouse also has an address and a name.  

A warehouse corresponds also to a location.  As the locations are hierarchical, OpenERP links a warehouse with one parent location that contains all the different sublocations in the warehouse.  

When you create a warehouse, the system will create the necessary picking types and parent locations in the background.  


============
MTO and MTS
============

A product can be MTO or MTS.  When a product is handled MTO, it means we will handle each order (e.g. sale order) individually and procure what is necessary, separately for every order.  When a product is handled MTS, we wait until there are sufficient orders and then we order everything at once taking into account a minimum stock (or a stock forecast) into account.  In OpenERP, we can automate minimum stock rules through orderpoints as shown in the next chapter. 

================
States of moves
================

* Draft
* Confirmed (Waiting Availability)
* Waiting (Waiting Another Move)
* Assigned (Available / Ready to Transfer)
* Done (Transferred)
* Cancel (Cancelled)

When we start to create a move, it will be in draft state.  This means, it will have no influence on even the virtual stock of the product.  It is only when we confirm the move that we make clear to the system that this move will be executed and should be taken into account for ordering new products.  The next state will however be different according to the scenario.  For example, if the product is MTO, in the stock location, it will wait for a specific purchase order and will have the Waiting Another Move state.  In case of an MTS product, the move will be configured as such that it will look for available stock in the source location itself and it will go to the Confirmed state.  

In these states it is possible to do "Check Availability".  If it can find the necessary stock, the state goes to Assigned.  In this state it is possible to effectively execute the move and transfer the products.  Incoming shipments are automatically available.  Effectively executing the move, brings it to the done state and makes it adapt the stock available on hand.  (quantity on hand)

Normally, the picking associated to the move, will have the same state as it moves, but the picking can also have a partially available state.  It is possible that some products in the picking are available and some are not.  On a sales order or delivery order picking, you can specify if you want your customer to be delivered as soon as possible when only a part of the products is  available (partial delivery) or only all at once when everything is available (in order to save on transport costs for example).  So, if you can do a partial delivery, the picking state will be partially available when only some of the products are available.  

==============================================
Orderpoints, procurement and procurement group
==============================================

Procurements represent needs that need to be solved.  For example, every sales order line will create a procurement in Customers.  This will be solved by a move for the delivery, which will, in case of a MTO product in buy configuration, create a new procurement (need) in Stock, which will be solved by a purchase order. 

It is not required however, to have this need in stock created by a move.  In case of MTS, the move will not create a procurement (need), but the the procurement will originate from an orderpoint created for this product in stock.  

An orderpoint applies the following rule: if the virtual stock for the given location is lower than the minimum stock indicated in the rule, the system will automatically propose a procurement to increase the level of virtual stock to the maximum level given in the rule.  We underline that the rule is based on virtual quantities and not just on real quantities. It takes into account the calculation of orders and receipts to come.

You can also set multiple quantities in the minimum stock rules. If you set a multiple quantity of 3 the system will propose procurement of 15 pieces, and not the 13 it really needs. In this case, it automatically rounds the quantity upwards.

Pay attention to the fact that the maximum quantity is not the maximum you will have in stock. If we take the following situation: a company has 10 pieces of product with minimum stock rules defined for this product by Min quantity = 10, Max quantity = 30 and Qty multiple = 12. If an order of 2 pieces comes, a purchase of 24 pieces order will be executed. The first 12 pieces will be ordered to reach the minimum quantity and the other 12 to reach the maximum quantity. At the end, the stock of this product will be equal to 32 pieces.

Scheduler: 

In order for the orderpoint to create the procurement, we need to launch the scheduler.  This can be done manually in Warehouse > ..., but will normally be automated by a scheduled action.  (by default it is automated on a daily basis)

Procurement groups: 

Suppose you have multiple lines in your sales order, then you want one delivery order with all the lines of the sales order.  In order to do that, we group the different procurements of this sale order into the same procurement group we create for the sales order.  


2 Standard configuration
************************

In this chapter, we want to show how to work with the simplest warehouse configuration.  (product MTO, product MTS with orderpoint, ...)

Suppose we have a little Apple Store.  The warehouse will be Apple Store and we manage only one location (no child locations).  We put a minimum stock of 10 iPad mini and 5 iPod nano.  We don't have stock for iBooks, but when a customer wants one, he can order one and will get it after a week.  

We create an orderpoint for every product.  Suppose the products are (for the mts products we could e.g. use the point of sale) for the 

<<Show where we put supplier info>>
<<Show where we configure buy and mto>>
<<Show how to configure orderpoints>>


3 Beyond the magic of stock moves
*********************************

=================================
Assigning stock moves to pickings
=================================

When you will create moves manually, you will normally do it by creating them within a picking.  When OpenERP will create stock moves, for example when the user confirms a sale order, it will create them without picking first.  In a second step, they will be attributed to an existing picking or a picking will be created.  

In order to assign the move to a picking, OpenERP will check if the move was assigned a picking type (e.g. Your Company: Delivery Orders) and if it does, it will search for a picking where it can put the move.  This picking should be in the right state, picking type, procurement group (=group of procurements related to e.g. the same sale order) and source and destination.  If no picking can be found, it will create one.  

In fact, a picking is almost entirely determined by the moves in it.  The state depends on the moves, the source and destination location are those of the moves and this is of course also the case for the picking type.  The scheduled date is calculated as a minimum date for the stock moves.  

How the state of a picking depends primarily on its moves: 

* If any move is draft, the picking is draft
* If all moves are done/cancel, the picking is done/cancel

The other states depend however also on the move_type. The move type determines whether the customer expects to get all products of a picking at once (=all at once) or he wants it delivered to him as fast as possible. (=partial)  This move type can be determined manually, or can e.g. come from a sale order where it will be passed through the procurement group.  

In case of partial, a special state exists: partial availability.  It is possible that a move is in the confirmed / waiting state, but has partially some stock reserved.  This move will still be in the waiting/confirmed state, but have a flag partially available.  In that case, the picking will not stay in the confirmed/waiting state but go to the partially available state, which makes it possible to deliver the goods partially.  A picking is also partially available when some moves are assigned and others have no stock at all reserved.  

Sometimes a move does not get assigned a picking type and it will not get assigned to a picking.  This is the case for inventory corrections and moves in and out of production. 


==============================
Procure method of stock moves
==============================

When a user creates a stock move in a picking, the stock move will have its procure method 'not to create procurements on source'.  This means it will not create a procurement in the source location created to the move and will try to find the products in the available stock of the source location.  

If the user chooses however to change the procure method to 'Create Procurement on Source', a procurement will be created in the source location.  A procurement represents a need in its location and this need has to be solved by certain rules defined in the system called pull rules (or procurement rules).  For example the rule can tell to create a purchase order to that location or to create another move with a certain procure method.  

For example, when we create a sale order for an MTO product, a procurement will be created in Customers.  The rules will tell that this should be solved by a move with procure method "Create Procurement" from Stock to Customers.  This move will create a procurement in its source location that will be solved by a rule telling to buy from a supplier.  That way a chain is created of moves waiting for each other.  


=============
Chained Moves
=============

Chained moves can be created with procurement rules, but another type of rule exists.  Push rules can be defined on destination locations.  When a move is confirmed and a push rules is defined on its destination location, it will create a move from the previous destination location towards a new destination location.  These rules come in handy when creating purchase orders manually and we want to receive in an Input location at the gates first, before transferring them to the stock in the racks.  Push rules will not be applied when the move was created from procurement rules.  On outgoing side, push rules will normally not be used.  

One move can have several original moves, but only one destination move.  When confirming a move with original moves (or split from a move with original moves), the move will go to the waiting state (Waiting Another Move) as it will wait for its previous moves to be executed.  

========================================================
Applied to MTO and MTS products and sale order and dates
========================================================

<< Orderpoints will also create procurements and have a different effect on the dates >>



========================
Procurement Exceptions
=======================

It is possible that a procurement is created, but no matching rule can be found to solve that procurement, or a buy rule is found, but no supplier is found to purchase from.  Then the procurement changes its state to exception.  If you go to Warehouse > Procurements you can filter on all exceptions.  When you corrected the problem by for example assigning a supplier to a product, you can go back and 

<<Maybe put this in chapter 2 instead>>





4 Complex logistic flows
************************

<<Check setting needed to activate>>

A lot of Warehouses have input docks and output docks or have a packing zone where people want to repack the packages for the customer.  This can become quite complex and in order to manage this better, we group procurement rules and push rules into routes before having them applied to product, product categories, warehouses, ...

Using these routes is simple as you just need to select them on e.g. a product or product category, but configuring them correctly is a little more difficult.  This is the reason why OpenERP will create the necessary routes automatically when you create a new warehouse.  Configuring the warehouse can then be a simple as choosing two step receival and 3 step delivery, will always be supplied from warehouse B, ...

We will however explain the routes as you might maybe enhance the basic config from OpenERP.  

======
Routes
======

A Route is a collection of procurement rules and push rules.  Routes can be applied on:

* Product
* Product Category
* Warehouse
* Sale Order Line (activated through setting Settings > Configuration > Sales > Choose MTO, Dropship, ... on sale order lines)

If they can be applied on these models can be specified on the route itself.  For example, you could create a route 'purchase' with the purchase procurement rule from stock in it allowed to be selected on Product Category.  Then you could go to the product category e.g. Purchased Goods and add it there. When a procurement is made in stock for the products in this category, the system will try to create purchase orders for it.  

===============================================================================
How does the system choose the correct procurement/push rule for a procurement?
===============================================================================

When a sales order creates a procurement it passes some useful information to it.  First, a sales order has a warehouse where the goods need to be picked up.  This warehouse will be copied on the procurement.  For example, when you have a procurement in Customers, but you know it has to be delivered from Warehouse WH, it can add a route with a procurement rule from WH/Stock to Customers and it will not apply a procurement rule from WH2/Stock to Customers.  Second, it is possible to supply an extra route on the sale order line itself.  This can come in handy when you decide on the sale order what route to follow e.g. if you sometimes decide to do dropshipping, you could enter it there.  These routes are copied on the procurement related to the sale order line.  

These routes on the procurement itself can also come in handy when the procurement can not find a suitable rule.  By adding a route, you can solve the procurement according to the situation.  (e.g. a certain product needs to be manufactured sometimes or bought sometimes) 

When OpenERP needs to find a procurement/push rule, it will check the routes that can be applied to the procurement as follows:  

* It will try to find a rule from the route(s) on the procurement first
* If it does not find any, it will try to find a rule from the route(s) on the product and product category (+ its parents)
* If it does not find any there, it will try to find a rule from the route(s) on the warehouse

If in any of these cases, multiple rules are found, it will select the rule with the highest sequence.  This sequence can be changed in Warehouse > Routes (drag/drop the lines).  Normally, this will play almost no role.  

Actually, when you select MTO on a product, this is a route that is chosen.  As in the basic configuration, it is defined on the product. (it is shown in the product form in a special widget that shows all the possible elements it could have in the one2many and you can select them)  As suchn this route will be chosen over the standard route and will have a rule that puts procure method "Create Procurement on Source" to stock. In the route MTO all such rules for all warehouses will be put in the standard configuration.  


========================
Simple Warehouse config
=======================

When you activate setting << >> and go to Warehouse > Warehouse and select a Warehouse (or create a new), you will have a simplified way to configure these routes without worrying about its complexity.  

For the incoming and outgoing shipments you can supply how many steps are needed to receive or ship goods.  This allows you e.g. to receive at the docks, and move the goods later on into a precise location in your racks.  It can also be interesting to do some quality control.  For shipping, you can also put your products at the gates first, but you might also want to package them at a separate location before bringing them at the gates. These routes will be directly related to the warehouse.  

If you check Purchase or Manufacture to resupply this warehouse, if a product is manufacture/buy, it will also be able to buy/manufacture from/in this warehouse. 

When you put a Default Resupply Warehouse, goods will always be supplied from this other Warehouse.  

You can choose multiple resupply warehouses.  These are selectable on the product / product category.  This is used when some products are supplied from one warehouse and others from another.  


===========================================
What happens behind simple warehouse config
===========================================

The wizard will create all the necessary locations and picking types to support the selected settings.  

The Incoming shipments and Outgoing shipments are bundled into routes that are on the warehouse.  So, if you choose that warehouse, it will choose the route by default.  

The purchase to resupply is a procurement rule added to the buy route, which will also buy to this warehouse. 





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

The removal strategy determines the order in which the stock gets reserved.  By default the removal strategy is FIFO (First In First Out).  

A different removal strategy can be defined by product category and location.  For example, for a certain category of products LIFO (Last In First Out) could be chosen when taking products from its stock location.  



==================
Packages and lots
==================

Quants (stock) can be put in a package and a package can be put in another package.  The same hierarchical structure can be used as for locations.  When pack A is put in pack B, its full name becomes PACK B / PACK A.  


Lots are always linked to a certain product and can be put as being required depending on the incoming/outgoing/full traceability selected on the product. If in a picking you do not select a lot, it can take any lot (or even without lot).  If you select a lot, it has to take it. 



=======================
Pack operations
=======================

In order to define the operations that can be proposed / executed by the bar code interface, we create / process pack operations.  The stock moves itself will tell nothing about (from) which package / location/lot to take, in which location / package to put the goods.  That is the job of the pack operations.  

There are actually 2 types of pack operation: 

* Take entire package
* Take products from a certain package or not in a package


=========================
Preparing pack operations
=========================

If a picking will be processed by the bar code scanner, OpenERP will propose the pack operations that need to be executed.  If it is an incoming shipment, it will be based on the moves, otherwise it will use the stock that has been reserved already.  

The moves or reserved stock (quants) will be grouped by:

* Lot: lot of the quant or empty if from stock move
* Product: product of the quant or stock move
* Package: the package from the quant or empty if from stock move
* Source location: the location of the quant or the source location of the move
* Destination location: For that we need to apply the putaway strategies

The putway strategies are similar to the removal strategies, but determine for the original destination location a child location where the goods should be deposited (instead as for the source location).  By default, there is no putaway strategy defined on the destination location.  In that case, the goods will be deposited in the destination location of the move.  In the stock module, there is one putaway strategy: fixed location.  For each such strategy you can also specify the related location.  Of course, based on this, custom developments make it possible to implement the putaway strategy you want (as it is applied on all of the stock being moved at once).

For the reserved stock, OpenERP will try to find as many packages (and as high-level) as possible for which the stock is entirely reserved and the destination location is the same for every piece of stock.  That way, the operator knows he can simply move the package to the destination location, instead of having to open the box and split the quantities.  

An example might illustrate this further:

Some pallets with product A and some mixed pallets with product A en B are placed at the gates and need to be moved to stock.  A picking proposes to move all products A and B to stock.  Product A has loc A as fixed location putaway strategy and product B has loc B as fixed location.  In the pack operations, OpenERP will make an operation by pack for all pallets with only product A all to the loc A.  For the mixed pallets, it won't be able to make one pack operation.  It will say: move the product A from the mixed pallet to loc A and move the product B from the mixed pallet to loc B.  


============
Unreserving
============
If we want to use a certain piece of stock on another picking instead of the picking selected, we can unreserve this piece of stock by clicking on the Unreserve button of the picking.  

It is however possible that during the pack operations, the guy has chosen the stock from another location.  In that case, other quants need to be reserved also.  When processing this picking further on, the system will unreserve the stock and do the reserve process again, taking into account the created pack operations from the bar code scanner interface.  




6 Transferring
***************

========================================================
Recomputation of links between moves and pack operations
========================================================


We need to check if the pack operations cover all moves and opposite.  If there is more of a product transferred in a pack operation than in the moves, an extra move needs to be created in the picking and set to done.  When there is less product in the pack operation than in the move, a backorder needs to be created with those moves and the original move might be split with a part going into the backorder.  

In order to do this matching, the system will try to match with stock reserved for a certain move.  It will loop through the pack operations and see if it can find the necessary stock it can match.  That way it will match quantities from the reserved stock move on the quant with the operation.  

If not everything could be matched with the reserved stock (e.g. an incoming shipment, this is always the case for the entire picking) it will match the remaining quantities on the moves with those of the packing operations.  

<< Need to tell about partial availability here? >>

This function can also be used to check the effect of the current pack operations, but tell also if the reservation is actually used or not.  If not, when transferring, it will have to rereserve the quants.  (unreserve + reserve)



=====================
Actual transferring
=====================

If there are pack operations, it will look the matching, find the quants accordingly and move them.  

If not, it will find the quants based on the moves only. 



======================
Negative stocks
======================

It is still possible that upon transferring for an internal shipment or delivery, the necessary quants or stock can not be found.  In that case, it will create negative stock (negative quants).    

When later on, a move brings in some goods that correspond to this negative stock, the quant can be reconciled with it.  This will however not happen if this incoming quant has a chained move to another location.  It is only when you force assign a move with original moves that it can also take from the regular stock (so not coming from its original moves).  It will however not assign this stock before actually doing the transfer.  


7 Returns and cancellation
***************************

========================
Returns
========================

It is possible to create a return on a done picking.  This wizard will propose to return everything that is still in the destination location.   


======================
Cancellation
======================

When you cancel a procurement, it will cancel everything in the backwards direction. When you cancel a move itself, it will cancel in the forward direction. 

This will happen only if the move has the attribute 'Propagate Cancel and Split' set to true.  Also, when a procurement rule (or a push rule) is applied to create another move, it will copy its 'Propagate Cancel and Split' on the move.  


8 Inventory
***********

When you start using OpenERP, you might have an inventory to start from.  (Starting Inventory)  You will enter all the products that are in the warehouse and OpenERP will put them in this position.  When you validate this inventory, OpenERP will create the necessary stock moves.  

It is possible that operations in the warehouse are not well registered and the stock in OpenERP does not correspond exactly to the physical stock in the warehouse.  Of course, you do not want this to happen, but errors do happen and a way to solve these mistakes, is to check the inventory once and a while.  

You can decide to do a certain product or a certain location.  So, you are not required to do all the invento



9 Examples pick pack ship
**************************






























