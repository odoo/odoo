==========================================
Odoo Mexico Localization for Stock/Landing
==========================================

This module extends the functionality of Mexican localization to support
customs numbers related with landed costs when you generate the electronic
invoice.

Usage
=====

To use this module, you need to:

* Generate a new purchase order for a product from abroad. Landed costs are
  only possible for products configured with 'automated' valuation with
  'FIFO' costing method. The costing method is configured in the product
  category.

.. figure:: static/description/purchase_order_new.png

* Receive the product of the purchase order

.. figure:: static/description/picking_done_purchase.png

* Go to Inventory -> Inventory control -> Landed Cost

* Create a new landed cost indicating the picking of the purchase order
  and the number of the customs information (pedimento). Landed costs are
  only possible for products configured in real time valuation with real
  price costing method. The costing method is configured on the product
  category

.. figure:: static/description/landed_cost_picking.png

* Start by creating specific products to indicate your various Landed
  Costs, such as freight, insurance or custom duties.

  Go to Inventory -> Configuration -> Landed Cost types. Landed costs are
  only possible for products configured in real time valuation with real
  price costing method. The costing method is configured on the product
  category.

.. figure:: static/description/product_landed_cost.png

* Click the Compute button to see how the landed costs will be split across
  the picking lines.

.. figure:: static/description/compute_landed_cost.png

* To confirm the landed costs attribution, click on the Validate button.

.. figure:: static/description/validate_landed_cost.png

* Create a sales order for the product purchased from abroad

.. figure:: static/description/sale_order_new.png

* Delivery the product related to the sales order

.. figure:: static/description/picking_done_sale.png

* Create and validate a new invoice associated with the sales order

.. figure:: static/description/validate_invoice_customs.png

* The customs information is found in the lines of the invoice associated
  with each product.

.. figure:: static/description/invoice_custom_pedimento.png

* Check the electronic invoice associated with the product where the node
  of the customs information is displayed

.. figure:: static/description/invoice_custom_xml.png
