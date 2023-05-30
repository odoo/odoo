/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "./tour_utils";

registry.category("web_tour.tours").add("self_order_after_meal_product_tour", {
    test: true,
    steps: [
        // Verify if the self is open
        PosSelf.check.isNotNotification(),
        PosSelf.check.isNotPrimaryBtn("My Orders"),

        // Add some products
        PosSelf.action.clickPrimaryBtn("View Menu"),
        ...PosSelf.action.addProduct("Large Cabinet", 15),
        ...PosSelf.action.addProduct("Office Chair Black", 3),
        ...PosSelf.action.addProduct("Conference Chair (Aluminium)", 7),

        // Check if products in the products list have their quantity
        // They should have because in "meal" mode we add products always to the same order
        PosSelf.check.isProductQuantity("Large Cabinet", 15),
        PosSelf.check.isProductQuantity("Office Chair Black", 3),
        PosSelf.check.isProductQuantity("Conference Chair (Aluminium)", 7),
    ],
});
