/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "./tour_utils";

registry.category("web_tour.tours").add("test_self_order_my_orders_tour", {
    test: true,
    steps: () => [
        // Verify if the self is open and My Orders is not displayed because we are in "meal" mode
        PosSelf.isNotNotification(),
        PosSelf.isNotPrimaryBtn("My Orders"),
        PosSelf.action.clickPrimaryBtn("View Menu"),

        ...PosSelf.action.addProduct("Office Chair Black", 1),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.isOrderline("Office Chair Black", "138.58", ""),

        PosSelf.action.clickPrimaryBtn("Order"),
        PosSelf.tablePopupIsShown(),
        PosSelf.action.selectTable({ id: "1", name: "1" }),
        PosSelf.action.clickPrimaryBtn("Confirm"),
        PosSelf.isNotification("Your order has been placed!"),
        PosSelf.action.clickPrimaryBtn("My Orders"),
        PosSelf.isOrderline("Office Chair Black", "138.58", ""),
    ],
});
