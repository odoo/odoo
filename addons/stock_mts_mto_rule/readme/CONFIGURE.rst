You have to select 'Use MTO+MTS rules' on the company's warehouse form.

Known issues
============

If you cancel a delivery order and then recreate it from Recreate
Delivery Order button in sale order form, then the stock level at the time of
the Re-Creation won't be taken into account. So if a purchase order was created
when the sale order was first validated, a similar purchase order will be created
during the Re-creation of the delivery order, even if not needed regarding the actual stock.
