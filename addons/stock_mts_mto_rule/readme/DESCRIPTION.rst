This module add a Make To Stock + Make to Order Route.

If you choose the make to stock + make to order rule instead of the make to
order route, the creation of a purchase order will depend on the virtual stock.
There are 3 cases :

1. The virtual stock of the product is 0
    => It will act exactly like the make to order route.

2. The virtual stock is equal to the quantity ordered
    => It will act exactly like a make to stock route

3. The virtual stock is more than 0 but less than ordered quantity
    => On part of the products will be taken from stock and a purchase order
       will be created for the rest. So it will act like both make to order and
       make to stock rule.

Example :
We have a virtual stock of : 1 product A
A sale Order is made for 3 products A.
2 Procurements will be created :

1. 1 with a make to stock rule and a quantity of 1

2. 1 with a make to order rule and a quantity of 2.

After validation, a purchase order with 2 products will be created.
