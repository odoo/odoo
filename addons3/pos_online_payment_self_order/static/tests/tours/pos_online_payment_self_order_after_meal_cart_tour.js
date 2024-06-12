/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "@pos_self_order/../tests/tours/tour_utils";

registry.category("web_tour.tours").add("pos_online_payment_self_order_after_meal_cart_tour", {
    test: true,
    steps: () => [
        // Check that the self is open
        PosSelf.isNotNotification(),

        PosSelf.action.clickPrimaryBtn("View Menu"),
        ...PosSelf.action.addProduct("Office Chair Black", 1),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.isOrderline("Office Chair Black", "138.58", ""),

        PosSelf.action.clickPrimaryBtn("Order"),
        PosSelf.tablePopupIsShown(),
        PosSelf.action.selectTable({ id: "1", name: "1" }),
        PosSelf.action.clickPrimaryBtn("Confirm"),
        PosSelf.isNotification("Your order has been placed!"),
        PosSelf.isPrimaryBtn("Pay"), // Not clicked on because it would open another page, losing the tour setup.

        // Modification of the order
        PosSelf.action.clickBack(),
        ...PosSelf.action.addProduct("Funghi", 1),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.isOrderline("Funghi", "8.05", ""),

        PosSelf.action.clickPrimaryBtn("Order"),
        PosSelf.isNotification("Your order has been placed!"),
        PosSelf.isPrimaryBtn("Pay"), // Not clicked on because it would open another page, losing the tour setup.

        // No modification of the order
        PosSelf.action.clickBack(),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.isOrderline("Office Chair Black", "138.58", ""),
        PosSelf.isOrderline("Funghi", "8.05", ""),

        PosSelf.isPrimaryBtn("Pay"), // Not clicked on because it would open another page, losing the tour setup.
    ],
});
