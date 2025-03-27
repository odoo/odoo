By default, Odoo allows negative stock. The advantage of negative stock
is that, if some stock levels are wrong in the ERP, you will not be blocked
when validating the picking for a customer... so you will still be able to
ship the products on time (it's an example !). The problem is that, after you
forced the stock level to negative, you are supposed to fix the stock level
later via an inventory ; but this action is often forgotten by users,
so you end up with negative stock levels in your ERP and it can stay like
this forever (or at least until the next full inventory).

If you disallow negative stock in Odoo with this module, you will be blocked
when trying to validate a stock operation that will set the stock level of
a product and/or location as negative. So you will have to fix the
wrong stock level of that product without delay, in order to validate the
stock operation in Odoo...you can't forget it anymore !
