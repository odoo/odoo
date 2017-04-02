FIFO/LIFO

In order to activate FIFO/LIFO, the costing method in the product form should be fifo/lifo.  This is only possible when cost methods are checked under Settings > Purchase



Normal case:
------------

= When product is purchased by purchase order and leaves towards a customer with a delivery order.  We assume also 
that accounting entries are generated in real-time.  

- When product is received, the stock move gets the unit price and UoM of the purchase order
- In the stock journal, the accounting items will be generated based on this.  
- When a delivery order is made, the FIFO/LIFO algorithm is used to check which in moves correspond to this out move.  A weighted average is calculated 
based on the different in moves which would theoretically have gone out according to the FIFO/LIFO algorithm.  This average becomes also the new cost price on the product.  
Technically, these calculated matchings are saved in stock_move_matching which makes further FIFO/LIFO calculations easier.  
- When generating accounting entries, the stock.move.matching table is used, to generate 1 account move line per matching.  That way, one stock move will have one account 
move with multiple account move lines with the amounts from the matchings.   


Case of production: 
-------------------
In case of produced goods, the incoming stock move of the finished product and accounting entries can not just invent a cost price like the sum of the cost price of the parts in the BoM, as costing methods tend to be a lot more complicated than this. 
On the stock move, we will put the cost price of the product.  

Case of no purchase order
-------------------------
When no purchase order is given, the price on the stock move and generated entries is the standard price on the product.  


Returned Goods / Scrap / ...
----------------------------
Returned goods to supplier have the same calculations as a normal out, same with scrap.  


Negative stocks
---------------
When an out move makes the stock (quantity on hand) become negative, the cost price of the product is not updated and stock move matchings will only be created for the moves that can be matched.  (until stock is zero)  If the quantity on hand became negative and afterwards we get an incoming move, the system will try to match the previous outgoing move(s) as much as possible with the incoming move.  These matches will generate also the necessary accounting entries.  


Inter-company
-------------
cost price, costing method and valuation (real_time or manual_periodic) are properties (are different according to the company) => when you receive/ship goods, it depends on the company of the stock move as what costing method needs to be used. 

Not possible to create a stock move between two locations of different companies.  You need a transit location in between.  This new constraint removes the requirement for a currency or two prices on one stock move.  

UoMs: As quantities need to be matched between outgoing and ingoing stock moves which can have different UoMs, it will take all these conversions into account

Currency: On the stock move, the currency is the company currency
