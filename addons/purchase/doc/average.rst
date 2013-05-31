Average price


Normal case:
------------

= When the product is purchased by purchase order and leaves towards a customer with a delivery order.  We assume also 
that accounting entries are generated in real-time.  

- When the products are received, the stock move gets the unit price and UoM of the purchase order in company currency.  The standard price of the product is updated with 
(qty available * standard price + incoming qty * purchase price) / (qty available + incoming qty)
- In the stock journal, the accounting items will be generated based on this (price on move is price of purchase order)
- When a delivery order is made, it is going out at cost price (= average price which was updated during incoming move)
- When generating outgoing accounting entries, this is the total amount based on this average cost price


Case of production: 
-------------------
In case of produced goods, the incoming stock move of the finished product and accounting entries can not just invent a cost price like the sum of the cost price of the parts in the BoM, as cost methods tend to be a lot more complicated than this. 
When the finished good is produced, we will put the cost price from the product.  

In the product form there is a link next to the cost price where the user can update it.  This will also generate accounting entries as the stock will be valued differently.  


Case of no purchase order
-------------------------
When no purchase order is given, the price on the stock move and generated entries is the cost price on the product


Returned Goods / Scrap / ...
----------------------------
For returning goods to supplier, the price on the original purchase order is put on the stock and account moves.  That way, this would have the same effect as cancelling the original in move.  
Scrap is an outgoing move at cost price.   


Negative stock
--------------
If your stock is negative and you receive, the price of the product becomes the price on the purchase order.  

Extra
-----
- standard price, costing method and valuation (real_time or manual) are properties.  This means it is possible to use the same product in different companies with different price, valuation and costing methods. 

- UoMs: On the stock move, the price is in units of the stock move, so this will get converted to the product UoM and reverse

- Currency: On the stock move, the currency is the company currency
