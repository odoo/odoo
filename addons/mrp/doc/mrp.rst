MRP 

In this chapter, we are going to explain briefly how to use mrp in its simplest form (without the mrp operations) and the impact on stock.  We suppose you know the terms used in the warehouse documentation.  

Order flow
**********

An order can be created manually or through the creation of a procurement.  

Important for stock management are the raw materials location and finished products location.  Creating a manufacturing order manually, this is by default equal to the location of the standard warehouse.  In case of a manufacturing order from a procurement, it will have the source location of the applied procurement rule as both the raw materials and finished products location.  

For a draft manufacturing order, you can change the products to consume, but not anything else.  The consumed products tab and the finished products tab will give the progress of the raw materials and finished products consumed/produced.  A left table described what needs to be produced and the right table what has been produced/consumed.  Behind the scenes, these are stock moves from the raw materials location to the production location (virtual) or from the production location (virtual) to the finished products location. 

First, the system will calculate the scheduled products from the bill of material and the quantity necessary.  These will be added to the scheduled products (third tab) and to the products to consume upon confirmation of the manufacturing order.  

The manufacturing order becomes ready to produce when the different moves are assigned (ready to transfer).  It is also possible to force the reservation (not recommended).  

Then you can also Mark as Started. 

When you click Produce, a wizard will be opened, where you can enter the quantity produced.  Based upon the quantity of finished goods produced, OpenERP will give you the theoretical amount that should still be produced.  The theoretical amount is actualy the ('percentage of finished products after this production' * scheduled amount of raw materials) - raw materials consumed.  

The advantage to the wizard  (instead of the arrows in v7) is in case of traceability.  Actually, if the raw materials and the finished goods require traceability, you should be able to specify for which finished good the raw material has been used. (requires lot for finished product and raw material)  That way, it is possible to do the full traceability in production.  

It is possible also to cancel a production order.  The products consumed/produced until then, will stay, but every move left, will be cancelled.  












