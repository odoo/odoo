Stock Module
++++++++++++

This module can be applied for simple stock management, but also for complex warehouse(s) management.  That is why, after having explained the main principles briefly, we will dedicate one chapter on how to use the warehouse management in its simplest form.  From the third chapter on, we will explain every step in more detail, allowing you to discover the full potential of the module.  


1 Main principles explained briefly
***********************************

============================================
Stock moves, locations, pickings and picking types
============================================

Some product will be moved between two different locations by stock moves. We want to be able to move multiple products at once however. That is why the stock moves will be bundled into pickings.  These pickings can e.g. be printed out or be processed on a bar code scanner interface as an assignment to someone in the warehouse.  As a user, the easy way is to create pickings at once.  

We also want to distinguish between several kind of pickings: the picking type.  In the simplest case, we want to distinguish between incoming, internal and outgoing shipments in the newest warehouse, as in the dashboard Warehouse > All Operations.  This is also an easy way to follow up the daily operations.  It gives you an idea of the amount of late pickings and the amount of backorders to process.  

You might have a weird feeling talking about moving from location A to location B, even for deliveries and incoming shipment.  That is because OpenERP uses a double-entry concept similar to double-entry accounting.  In OpenERP you do not talk of disappearance, consumption or loss of products: instead you speak only about stock moves from one place to another.

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

A warehouse represents the building where we stock our goods.  In case of multiple warehouses, you can enter the warehouse on your purchase orders and sale orders, such that the transport knows where to deliver / get it.   

However a warehouse also corresponds to one location.  As the locations are hierarchical, OpenERP links a warehouse with one location that contains all the different sublocations in the warehouse.  

<<Relation between picking types and warehouse >>


============
MTO and MTS
============

A product can be MTO or MTS.  When a product is handled MTO, it means we will handle each order (e.g. sale order) individually and procure what is necessary, separately for every order.  When a product is handled MTS, we wait until there are sufficient orders and then we order everything at once + some extra to take a minimum stock (or a stock forecast) into account.  In OpenERP, we can automate minimum stock rules through orderpoints as shown in the next chapter. 

================
States of moves
================

* Draft
* Confirmed (Waiting Availability)
* Waiting (Waiting Another Move)
* Assigned (Available / Ready to Transfer)
* Done (Transferred)
* Cancel (Cancelled)

When we start to create a move, it will be in draft state.  This means, it will have no influence on even the virtual stock of the product.  It is only when we confirm the move that we make clear to the system that this move will be executed and should be taken into account for ordering new products.  The next state will however be different according to the scenario.  For example, if the product is MTO, in the stock location, it will wait for a specific purchase order and will have the Waiting Another Move state.  In case of MTS it will go to the Confirmed state.  

In these states it is possible to do "Check Availability" (or to Force Availability if you don't mind negative stocks).  If it can find the necessary stock, the state goes to Assigned.  This makes it possible to effectively execute the move and transfer the products.  Incoming shipments are automatically available.  Effectively executing the move, brings it to the done state and makes it adapt the stock available on hand.  (quantity on hand)


<<Procurement and Procurement Group>>


<<Properties of moves: all at once, ...>>


<<Scheduler>>


2 Standard configuration
************************

In this chapter, we want to show how to work with the simplest warehouse configuration.  (product MTO, product MTS with orderpoint, ...)






3 Beyond the magic of stock moves
*********************************

=================================
Assigning stock moves to pickings
=================================

As a user creating warehouse operations manually, you will not create moves normally, but entire pickings at once.  OpenERP will however create moves automatically.  For example, when confirming a sales order, it might create the moves towards Customer.  However, you want them to be bundled in a Delivery Order picking.  After confirmation of a move, OpenERP will check if the move was attributed a picking type (e.g. Your Company: Delivery Orders) and if it does, it will search for a picking where it can put the move.  This picking should be in the right state, picking type, procurement group (=group of procurements related to e.g. the same sale order) and source and destination.  If no picking can be found, it will create one.  

The state, the source and destination location, the scheduled date and the picking type of a picking depend entirely on the moves in it.  Technically, these are function/related fields.  (previous workflow was removed also) 

<<Depending on move type, normal states also change>>

For the state, a special case exists: partial availability.  It is possible that a move is in the confirmed /waitingstate, but has partially some stock reserved.  This move will be partially available.  A picking has a move type (which will be passed through the procurement group from e.g. a sales order) that will tell if a customer expects to get everything delivered at once or expects several deliveries when the products are available.  In the latter case, the picking will not stay in the confirmed/waiting state but go to the partially available state, which makes it possible to deliver the goods partially.  

Sometimes a move does not get assigned a picking type and it will not get assigned to a picking.  This is the case for inventory corrections and moves in and out of production. 


==============================
Procure method of stock moves
==============================

When a user creates a stock move in a picking, the stock move will have its procure method not to create procurements on source.  This means it will not create a procurement in the source location created to the move and will try to find the products in the available stock of the source location.  

If the user chooses however to change the procure method to 'Create Procurement on Source', a procurement will be created in the source location.  A procurement represents a need in its location and this need has to be solved by certain rules defined in the system called pull rules (or procurement rules).  For example the rule can tell to create a purchase order to that location or to create another move with a certain procure method.  

For example, when we create a sale order for an MTO product, a procurement will be created in Customers.  The rules will tell that this should be solved by a move with procure method "Create Procurement" from Stock to Customers.  This move will create a procurement in its source location that will be solved by a rule telling to buy from a supplier.  That way a chain is created of moves waiting for each other.  


=============
Chained Moves
=============

Chained moves can be created with procurement rules, but another type of rule exists.  Push rules can be defined on destination locations.  It will create a move from the previous destination location towards a new destination location.  These rules are in handy when creating manual purchase orders, which make the goods arrive in Input and these goods need to be transferred to Stock afterwards or need to pass quality control for example.  


One move can have several original moves, but only one destination move.  When confirming a move with original moves (or split from a move with original moves), the move will go to the waiting state as it will wait for its previous moves to be executed.  

================================
Applied to MTO and MTS products and sale order and dates
===============================


<<Orderpoints will also create procurements and have a different effect on the dates>>


========================
Procurement Exceptions
=======================

It is possible that a procurement is created, but no matching rule can be found to solve that procurement, or a buy rule is found, but no supplier is found to purchase from.  Then the procurement changes its state to exception.  If you go to Warehouse > Procurements you can filter on all exceptions.  When you corrected the problem by for example assigning a supplier to a product, you can go back and 

<<Maybe put this in chapter 2 instead>>





4 Complex logistic flows
************************

<<Check setting needed to activate>>

Of course we want to do more complex flows than a simple in and out.  A lot of Warehouses have input docks and output docks or have a packing zone where people want to repack the packages for the customer.  This can become quite complex and in order to manage this better, we group procurement rules and push rules into routes before having them applied to product, product categories, warehouses, ...

The configuration of these routes can become quite complex and in order to simplify it is possible to configure the routes in a simpler way on the warehouse.  For example, the warehouse can be two step reception and 3 step delivery and be replenished from another warehouse, ...

======
Routes
======

A Route is a collection of procurement rules and push rules.  Routes can be applied on:

* Product
* Product Category
* Warehouse
* Sale Order Line (activated through setting <<..>>)

If they can be applied on these models can be specified on the route itself.  For example, you could create a route purchase with the purchase procurement rule from stock in it allowed to be selected on Product Category.  Then you could go to the product category e.g. Purchased Goods and add it there. When a procurement is made in stock for the products in this category, the system will try to create purchase orders for it.  



How does the system choose the correct procurement/push rule for a procurement?

When a sales order creates a procurement it passes some useful information to it.  First, on a sales order, a warehouse is supplied.  This warehouse will be copied on the procurement.  For example, when you have a procurement in Customers, but you know it has to be delivered from Warehouse WH, it can add a route with a procurement rule from WH/Stock to Customers.  Second, it is possible to supply an extra route on the sales order line itself.  This can come in handy when you decide on the sale order what route to follow e.g. if you sometimes decide to do dropshipping, you could supply it there.  These routes are put on the procurement itself.  

These routes on the procurement itself can also come in handy when the procurement can not find a suitable rule.  By adding a route, you can solve the procurement according to the situation.  (e.g. a certain product needs to be manufactured sometimes or bought sometimes) 

When the system wants to find a procurement/push rule, it will check all the routes that can be applied on the procurement first.  These are the routes on the procurement, the routes from the warehouse, the routes from the product and the routes from the product category (and its parents).  

* It will try to find a rule from the route(s) on the procurement first
* If it does not find any, it will try to find a rule from the route(s) on the product and product category (+ its parents)
* If it does not find any there, it will try to find a rule from the route(s) on the warehouse

If in any of these cases, multiple rules are found, it will select the rule with the highest sequence.  This sequence can be changed in Warehouse > Routes (drag/drop the lines).  Normally, this plays almost no role.  

Actually, when you select MTO on a product, this is actually a route that is chosen.  This route will be chosen over the standard route and will have a rule that puts procure method "Create Procurement on Source" to stock. In the route MTO all such rules for all warehouses could be put.  


========================
Simple Warehouse config
=======================

When you activate setting << >> and go to Warehouse > Warehouse and select a Warehouse (or create a new), you will have a simplified way to configure these routes without worrying about its complexity.  

For the incoming and outgoing shipments you can supply how many steps are needed to receive or ship goods.  This allows you for example to receive at the docks, and move the goods later on into a precise location in your racks.  It can also be interesting to do some quality control.  For shipping, you can also put your products at the gates first, but you might also want to package them at a separate location before bringing them at the gates. These routes will be directly related to the warehouse.  

If you check Purchase or Manufacture to resupply this warehouse, if a product is manufacture/buy, it will also be able to buy/manufacture from/in this warehouse. 

When you put a Default Resupply Warehouse, goods will always be supplied from this other Warehouse.  

You can choose multiple resupply warehouses.  These are selectable on the product / product category.  That can come in handy when some products are supplied from one warehouse and others from another.  


===========================================
What happens behind simple warehouse config
===========================================

The wizard will create all the necessary locations in the different 

The Incoming shipments and Outgoing shipments are bundled into routes that are on the warehouse.  So, if you choose that warehouse, it will choose the route by default.  

The purchase to resupply is a procurement rule added to the buy route, which will also buy to this warehouse.  Same for manufacturing. 





5 Reservation of stock and doing pack operations
************************************************

===========================================
Quants, reservations and removal strategies
===========================================

When you check availability or you do action_done on an original stock move or the scheduler sees your confirmed move, the system will try to reserve stock .  In v8, an extra model has been added to represent this stock, namely the quant.  So, reserving stock means choosing the right quants and tagging them as reserved for your move.  

In order to do so: we need to consider the following: 

* If there are original moves, the stock has to come from these moves
* If there are no original moves, it can take from the source location, but only if this stock has not been reserved on other moves
* Also in case of returned moves, the system needs to check it
* When choosing the stock, we need to take into account the removal strategy

By default the removal strategy is fifo.  This means the quant chosen is the stock that came in first into the system.    

A removal strategy can be put on a product category and location.  For example, for certain products lifo could be chosen in stock.  This mechanism can be used when you want to add other methods.  

In case of incoming shipments, we do not need to reserve stock or to apply removal strategies.  



======================
Packages and lots
==================

Quants(stock) can be put in packages, but also packages in packages as we gave the packages a hierarchical structure similar to the locations.  

Lots are always linked to a certain product and can be put as being required depending on the incoming/outgoing/full traceability selected on the product. If in a picking you do not select a lot, it can take any lot (or even without lot).  If you select a lot, it has to take it. 



=======================
Pack operations
=======================

Behind the bar code scanner interface, we need an extra model pack operations.  The stock moves itself will tell nothing about which packages to take, in which packages to put, which lots to take, from which location we need to take and in which location to put it.  That is the job of the pack operations.  

There are actually 2 types of pack operation: 

* Take entire package
* Take products from a certain package or that are not in a package


=========================
Preparing pack operations
=========================

Before a picking is handled by a bar code scanner, it is necessary to propose the pack operations based on the moves and the quants reserved.  It will start with the quants reserved and add until everything is chosen for the moves.  

This is done by checking the quants reserved and grouping those with the same:

* Lot: lot of the quant or empty if from stock move
* Product: product of the quant or stock move
* Package: the package from the quant or empty if from stock move
* Location source: the location of the quant or the source location of the move
* Location destination: For that we need to apply the putaway strategies

OpenERP will try to move entire packages as much as possible instead of parts of a package.  (based on these groupings)

The putway strategies are also defined on product category and location as is the case for the removal strategies.  

There is one putaway strategy defined in the system.  This can be used to define a fixed location for certain products.  


============
Unreserving
============
If we want to use a certain piece of stock on another picking instead of the picking selected, we can unreserve this piece of stock by clicking on the Unreserve button of the picking.  

It is however possible that during the pack operations, the guy has chosen the stock from another location.  In that case, other quants need to be reserved also.  When processing this picking further on, the system will unreserve the stock and do the reserve process again taking into account the created pack operations from the bar code scanner interface.  




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




8 Inventory
***********


9 Examples pick pack ship
**************************



















































