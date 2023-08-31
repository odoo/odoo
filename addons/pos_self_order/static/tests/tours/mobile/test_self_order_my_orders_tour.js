/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "../../utils/tour_utils";

registry.category("web_tour.tours").add("test_self_order_my_orders_tour", {
    test: true,
    steps: () => [
        // Verify if the self is open and My Orders is not displayed because we are in "meal" mode
        PosSelf.check.isNotNotification(),
        PosSelf.check.isNotPrimaryBtn("My Orders"),
        PosSelf.action.clickPrimaryBtn("View Menu"),

        ...PosSelf.action.addProduct("Office Chair Black", 1),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.check.isOrderline("Office Chair Black", "138.58", ""),

        PosSelf.action.clickPrimaryBtn("Order"),
        PosSelf.check.tablePopupIsShown(),
        PosSelf.action.selectTable({ id: "1", name: "1" }),
        PosSelf.action.clickPrimaryBtn("Confirm"),
        PosSelf.check.isNotification("Your order has been placed!"),
        PosSelf.action.clickPrimaryBtn("My Orders"),
        PosSelf.check.isOrderline("Office Chair Black", "138.58", ""),
    ],
});
