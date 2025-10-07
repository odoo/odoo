**********Delivery Order Customization for Sales Orders**********

*Overview*
This odoo16 module extends the Odoo Delivery Orders (DO) by adding a button that allows users to quickly navigate to the linked Sales Orders. It simplifies the process of accessing related Sales Orders directly from the Delivery Order form.

*Key Features*
Sales Order Link in Delivery Orders: Adds a sale_id field to the Delivery Order form, linking the DO to its originating Sales Order.

- Navigation Button: Introduces a button that redirects users to the linked Sales Order, enhancing the user experience by providing seamless navigation.
- Button Visibility: The button is only visible when the Delivery Order was generated from a Sales Order. If no Sales Order is linked, the button is hidden.
- Sales Order Count: Displays the count of linked Sales Orders directly in the Delivery Order view as a statistic.

*Installation*

- Download or clone this module into your Odoo addons directory.
- Update the Odoo apps list by going to Apps > Update Apps List.
- Install the "Delivery Order Customization for Sales Orders" module from the Odoo Apps menu.

*Usage*

Navigating from Delivery Orders to Sales Orders

1. Go to Inventory > Delivery Orders.
2. Open any Delivery Order that was generated from a Sales Order.
3. You will see a new "Sale" button with a count of linked Sales Orders.
4. Click the button to directly open the linked Sales Order.

Viewing Sales Order Count

1. In the Delivery Order form view, the count of related Sales Orders will be displayed as a statistic.
2. If the count is 0, the button will not appear.

*License*
This module is provided under the Odoo Proprietary License. See the LICENSE file for full details.

*Author*
Quocent Digital
https://www.quocent.com