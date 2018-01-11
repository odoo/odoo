Intrastat Module
++++++++++++++++

This module can generate legal electronic reports for intrastat declaration

1 Security groups
*****************

There's two security groups, a standard and an extended, that can be used to view/hide fields linked to the intrastat declaration. The extended group is mainly here to hide the two useless fields if you don't have to send an extended declaration, "Means of transport" and "Incoterm".

2 Intrastat codes
*****************

The system must be able to associate an intrastat code to each product exported. The system can do this in different ways.

Each product can have a category, and each category can have a parent category. To retrieve the intrastat code associated to a product, the system search in this order :

#. check if product have an intrastat code
#. if not, check if product's category have an intrastat code
#. if not, check parent category if it have an intrastat code
#. if not, check parent category of parent category if it have an intrastat code (and so on)
#. if none found, an error is shown

So, in a user point of view, to easily record your intrastat codes, you can procede on the low-level categories, and then, for the product in a category with a wrong code for this item, set the intrastat code in the product form

3 Country of destination
************************

Intrastat declares all movements from an EU member country to another. In an invoice, a zone called "intrastat country" is used to determine the destination of goods. If this field is empty, the invoiced partner's country is used.

==============
Direct invoice
==============

If you create an invoice directly, the intrastat country is empty by default, and the invoiced partner's country is used. If the country of destination is different from the country of invoice, simply fill in the field "Intrastat country".

=======================
Invoice from sale order
=======================

If you create an invoice from a sale order, there are two cases. If you're not using different addresses for invoicing and delivery, the country of the partner is used to fill in the "Intrastat country" of the invoice
If you're using different addresses, the country of delivery address is used, if there's none, the country of the partner's address, and if none, the country of invoice address.

=====================
Invoice from purchase
=====================

If you create an invoice from a purchase order, the "Intrastat country" field is filled with the partner address.

4 Regions, Type of transaction
******************************

In the intrastat declaration the system must fill an information regarding the region of origin of products, and an information regarding the type of transaction.

======
Region
======

The region of origin of products is determined by using two parameters. If your invoice is linked to a sale order or to a purchase order, the system go to the order, check if the order is linked to a warehouse, and check the warehouse region.

If the system hasn't find a region, the system goes to the company, and check the region of the company. If there's none, an error message is generated.

===================
Type of transaction
===================

Intrastat define a list of transactions types. To determine the type of transaction for a particular invoice, the system check if a transaction type is selected in the invoice. If not, the type 1 is selected by default.
