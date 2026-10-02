**Odoo Woocommerce Connector**
==============================

**Description**
***************

* Technical name: bad_connector_woocommerce.
* Add new menu in Connectors > Woocommerce > WooCommerce Backends.
* Add new menu in Connectors > Configrations > Settings.
* Add object woo.backend, woo.product.category, woo.product.image.url, woo.tax, woo.payment.gateway, woo.sale.status and woo.downloadable.product on submenu Connectors.
* Add object woo.settings, res.config.setting and woo.sale.status in Configuration submenu of woocommerce backend.
* Submenu of Configurations > WooCommerce Sale Status which is use to store all the WooCommerce Sale Order Status.
* Required field are Location,Client Key,Client Secret.
* 'Test' mode is used to test the environment using test data, while the 'Production' mode is used for the live environment that contains real customer data and requires production-level credentials.
* Create a module named bad_connector_woocommerce This module focuses on the import of "Customers", "Products","Product Attributes","Product Categories", "Taxes", "Orders", "Refunds" and export of "Orders" and its "Refunds" data between connected Woocommerce and Odoo.
* Add "Import Partners","Import Products","Import Product Templates","Import Product Attributes","Import Product Category", "Import Orders", "Sync Metadata", "Import Taxes", "Update Stock Inventory" and "Export Refunds" at backend level.
* Required field to Import the Partners,Product Templates,Products,Product Attributes,Taxes,Product Tags,Product Category,Update Stock Inventory, Sale Orders and Export Sale Order Refunds are Location,Client Id,Client Secret,Product Category,Company and Warehouse.
* Add Button of "GENERATE TOKEN" to generate the "Access Token".
* Added multi-warehouse functionality to manages stock.
* Multi company support.

**Author**
**********

* BizzAppDev


**Used by**
***********

* BizzAppDev


**Installation**
****************

* Under applications, the application bad_connector_woocommerce can be installed/uninstalled.


**Configuration**
*****************

* Woo Backend:
    - Add configuration details such as the Location, version, Client Key, and Client Secret to sync with the database.

* Partners Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Partners.
    - Click 'Import Partners' button to Import the Partners from Woocommerce.
    - When 'force_import_partners' boolean option is set to 'True', customers can be imported from Woocommerce,irrespective of whether the data is up-to-date or not.
    - At the WooCommerce backend level, a new boolean option 'Allow Partners without Email' has been introduced. When this option is set to 'True', the system will import all partners from child_ids that do not have an email. Conversely, when the option is set to 'False', the system will import only those partners from child_ids that have an email.

* Products Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Products.
    - Click the 'Import Products' button to import Products from WooCommerce.
    - When 'force_import_products' boolean option is set to 'True', products can be imported from Woocommerce,irrespective of whether the data is up-to-date or not.
    - At the WooCommerce backend level, a new boolean option 'Allow Product without SKU' has been introduced. When this option is set to 'True', the system will import all Products from WooCommerce that do not have an SKU. Conversely, when the option is set to 'False', the system will import only those Products from WooCommerce that have an SKU.
    - At the WooCommerce backend level, in 'Advanced Configuration' tab there is 'Product Category' from that select any category in which you have to keep your Product.
    - Added a Price,Regular Price,Stock Status,Tax Status,WooCommerce Product Attribute Values, and Status at the binding level.
    - Added 'Product Category' field which is located at Connectors> WooCommerce > Advanced Configuration which is use to Set Odoo Product Category for imported WooCommerce Product.
    - Added 'Default Product Type' field which is located at Connectors> WooCommerce > Advanced Configuration which is use to Set Odoo Product Type for imported WooCommerce Product.
    - Added 'WooCommerce Product Image URL' which is located at Product Binding level, designed to store Other Product Images which will store in woo.product.image.url object instead of initial Image.
    - Added 'WooCommerce Downloadable Product' which is located at Product Binding level, designed to store Downloadable Product files which will store in woo.downloadable.product object also The downloadable product in odoo is imported as Service type.
    - By Clicking the "Import Products" button different product type such as Simple and Variable will get imported from woocommerce in odoo.

* Product Templates Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Product Templates.
    - Click the 'Import Product Templates' button to import Product templates and it's variations from WooCommerce.
    - By Clicking the "Import Product Templates" button product type Variable will get imported from woocommerce in odoo.
    - When 'force_import_variable_products' boolean option is set to 'True', variable products can be imported from Woocommerce,irrespective of whether the data is up-to-date or not.
    - "Import Product Templates" follows same configurations as the "Import Products" functionality.

* Product Attributes Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Product Attributes.
    - Click the 'Import Product Attributes' button to import Product Attributes from WooCommerce.
    - After Import Product Attribute immediately Attribute Value will be imported and another way to Import and Update the Attribute Value is to Click the 'Import Attribute Value' button located in Product Attribute's form view.
    - The 'Product Attributes Value' menu item is located at Sale > Configuration > Product.
    - Product Attribute Value, add a "Group By" based on the Attribute.

* Product Categories Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Product Categories.
    - Click the 'Import Product Categories' button to import Product Categories from WooCommerce.
    - The 'WooCommerce Product Categories' menu item is located at Connector > WooCommerce > WooCommerce Product Categories.

* Product Tags Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Product Tags.
    - Click the 'Import Product Tags' button to import Product Tags from WooCommerce.

* Orders Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Orders.
    - Click 'Import Orders' button to Import the Orders from Woocommerce.

* Sync Metadata:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Metadata which contains Country, States, Tax Settings, Shipping Methods and Stock Manage Settings.
    - Add Backend Credentials to Import Metadata which contains Payment Gateways.
    - Add Backend Credentials to Import Metadata which contains default currency, Default Weight and Dimension.
    - Click the 'Sync Metadata' button to import Country and there States, Tax Settings, Shipping Method, Currency and Unit settings, Payment Gateways and Stock manage settings from WooCommerce.

* Taxes Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Taxes.
    - Click 'Import Taxes' button to Import the Taxes from Woocommerce.

* WooCommerce Webhook:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Generate the token to get the "Access Token".
    - Follow the step which is mention in "Webhook Configuration" Tab.

* Refunds Export:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Export Refunds.
    - Click 'Export Refunds' button to Export the Refunds to Woocommerce.

* Refunds Import:
    - Navigate to Woocommerce Backends by going to Connectors > WooCommerce > WooCommerce Backends.
    - Add Backend Credentials to Import Refunds.
    - Click 'Import Orders' button to Import the Refunds from Woocommerce.

**Usage**
*********

* This module, 'Connector Woocommerce,' acts as a connector or integration tool for facilitating interaction between the Woocommerce platform and Odoo.

* Import of Partner Data:
  - Enable the import functionality in bad_connector_woocommerce to transfer partners from Woocommerce to Odoo.
  - Handle mapping of partner data at time of Import Partners.
  - Added filter base of binding.

* Import of Product Data:
  - Enable the import functionality in bad_connector_woocommerce to transfer products from WooCommerce to Odoo.
  - Handle mapping of product data during the import process.
  - Introduces "import_products_from_date" fields at the backend level, allowing import from a specified date for getting updated products.
  - Implements import of Attributes and Categories during the product import.
  - Added woo_product_categ_ids and woo_attribute_ids in product binding level.
  - Added mapping of woo_product_attribute_value_ids in product binding level.
  - Enable the Export functionality in bad_connector_woocommerce to transfer Product Quantity from Odoo to WooCommerce.

* Import of Product Template Data:
  - Enable the import functionality in bad_connector_woocommerce to transfer product templates and variations from WooCommerce to Odoo.
  - Handle mapping of product template data during the import process.
  - Introduces "import_products_tmpl_from_date" fields at the backend level, allowing import from a specified date for getting updated product templates.
  - Implements import of Attributes and Categories during the product template import.
  - Added woo_product_categ_ids and woo_attribute_ids in product template binding level.
  - Added mapping of woo_product_attribute_value_ids in product template binding level.
  - Enable the Export functionality in bad_connector_woocommerce to transfer Product template Quantity from Odoo to WooCommerce.

* Import of Product Attribute:
  - Enable the import functionality in bad_connector_woocommerce to transfer product Attributes from WooCommerce to Odoo.
  * Import of Product Attribute Value:
  - Enable the import functionality in bad_connector_woocommerce to transfer product Attribute Values from WooCommerce to Odoo.
  - Handle mapping of product attribute data during the import process.

* Import of Product Categories:
  - Enable the import functionality in bad_connector_woocommerce to transfer product Categories from WooCommerce to Odoo.
  - Handle mapping of product categories data during the import process.
  - Set Product Category to category id in product if Woocommerce category matched with odoo categories.

* Import of Product Tags:
  - Enable the import functionality in bad_connector_woocommerce to transfer product Tags from WooCommerce to Odoo.
  - Handle mapping of product tags data during the import process.

* Import of Order Data:
  - Enable the import functionality in bad_connector_woocommerce to transfer Orders from Woocommerce to Odoo.
  - By selecting company in woocommerce backend, we can import sale order for that specific company.
  - Handle mapping of sale order data at time of Import Orders.
  - By selecting sale team in woocommerce backend, we can use it as default sale team while importing sale orders.
  - Enable the form of Sale Order Line and added 'WooCommarce Connector' in sale order line level and added related line calculated field at binding level of sale oder line.
  - Added related sale order amount field at binding level of sale order.
  - Added 'Export Delivery Status' button at sale order level and it will export the Status of sale order to 'Completed' state and carrier_tracking_ref which is located at Stock Picking level in 'Additional info' tab.
  - At backend level,'Mark Order Completed On Delivery' boolean which is located at connectors > WooCommerce > Advanced Configuration tab if 'Mark Order Completed On Delivery' is True then 'Send Tracking Information' will be visible and if 'Mark Order Completed On Delivery' True then State will set 'Completed' in WooCommerce of that Order if 'Mark Order Completed On Delivery' and 'Send Tracking Information' then it will set Order to 'Completed' state and also tracking info will also send in WooCommerce.
  - At sale order level, we can see the coupon code that are applied on Woocommerce order.
  - When the Price Tax, recorded at the Order Line level, differs from the Total Tax Line value, recorded at the Order Line's binding level, a 'The WooCommerce Price Tax is different then Total Tax of Odoo.' Danger Banner will be displayed at the sale order level.
  - When the Amount Total, recorded at the Order level, differs from the woo Amount Total value, recorded at the Order binding level, a 'The WooCommerce Amount Total is different then Amount Total of Odoo.' Danger Banner will be displayed at the sale order level.
  - At the backend level, within the 'Connectors' section, specifically under 'WooCommerce' > 'WooCommerce Backends' in the 'Advanced Configuration' tab, there is a 'Filter Sale Orders Based on their Status' Many2many Field. When this field is populated with specific sale order statuses, it will filter and retrieve those sale orders from WooCommerce that match the statuses provided in the 'Filter Sale Orders Based on their Status' field.
  - To set the WooCommerce status to "Completed," ensure that all corresponding sale orders have their delivery orders in either the "Done" or "Cancelled" state.

* Payload Information:
  - At Partner, Product, Product Attribute, Product Attribute Value, Country, Delivery Carrier, Product Tags and Sale order binding form view level the co-responding payload can be viewed in "Woo Data" field.

* Import of Taxes:
  - Enable the import functionality in bad_connector_woocommerce to transfer Taxes from WooCommerce to Odoo.
  - Handle mapping of taxes data during the import process.

* Import of Metadata:
  - Enable the import functionality in bad_connector_woocommerce to transfer Country and there States and also Tax Settings from WooCommerce to Odoo.
  - Handle Mapping of Country, State and Tax Settings data during the import process.
  - Added Mapping for State in Customers.
  - Added 'Tax Include' in field at backend level which get the setting of 'Tax Include'.
  - Added Condition on search tax base on 'Included in Price'.
  - Transfer Stock Manage Settings from WooCommerce to Odoo and handle the mapping during import process.

* Import of Webhook Record:
  - In the backend settings, navigate to the 'Connectors' section and select 'WooCommerce.' Within the 'WooCommerce Backends' subsection, locate the "GENERATE TOKEN" button, which is used to generate the necessary authentication token. In the "Webhook Configuration" tab, follow the outlined steps to establish the connection and receive webhook responses from WooCommerce to Odoo.

* Export of Refunds:
  - Enable the Export functionality in bad_connector_woocommerce to transfer Refunds from Odoo to WooCommerce.
  - Handle mapping of Refund data during the export process.
  - After confirming the Sale Order, validating the Delivery Order, Creating the Return with its Return Reason, and then validating the Return, there we added a new field called "Refund Quantity With Amount" at the stock.picking level. If the boolean associated with this field is set to True, it allows the export of refunds to WooCommerce by clicking on the "Export Refund" boolean.
  - Added "Export Refunds" button at the backend level. This button facilitates the export of all eligible returns for refunds.

* Import of Refunds:
  - Enable the Import functionality in bad_connector_woocommerce to transfer Refunds from WooCommerce to Odoo.
  - Handle mapping of Refund data during the Import process.
  - After Import the Sale Order, Validating the Delivery Order, and Then Click on "Import Order" from Backend Level to import the refunds from WooCommerce.

**Known issues/Roadmap**
************************

* #N/A


**Changelog**
*************

* #N/A
