{
    "name" : "Stock Location Paths",
    "version" : "1.0",
    "author" : "Tiny",
    "depends" : [ "stock"],
    "category" : "Generic Modules/Inventory Control",
    "description":"""
Manages product's path in locations.

This module may be usefull for different purposes:
* Manages the product in his whole manufacturing chain
* Manages different default locations by products
* Define paths within the warehouse to route products based on operations:
   - Quality Control
   - After Sales Services
   - Supplier Return
* Manage products to be rent.
    """,
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["stock_view.xml",
					"security/ir.model.access.csv",
				   ],
    "active": False,
    "installable": True
}

