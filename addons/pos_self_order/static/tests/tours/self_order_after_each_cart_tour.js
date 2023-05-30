/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosSelf } from "./tour_utils";

registry.category("web_tour.tours").add("self_order_after_each_cart_tour", {
    test: true,
    steps: [
        // Verify if the self is open and My Orders is not displayed because we are in "meal" mode
        PosSelf.check.isNotNotification(),
        PosSelf.check.isPrimaryBtn("My Orders"),
        PosSelf.action.clickPrimaryBtn("My Orders"),
        PosSelf.check.isNotification("found on the server"),
        PosSelf.action.clickBack(),
        PosSelf.action.clickPrimaryBtn("View Menu"),

        // Add some products
        ...PosSelf.action.addProduct("Office Chair Black", 1),
        ...PosSelf.action.addProduct("Office Chair Black", 2, "Description"),
        ...PosSelf.action.addProduct("Large Cabinet", 2),
        PosSelf.action.clickPrimaryBtn("Review"),

        // Here we're looking at whether when an orderline is clicked on from
        // the cart and edited, the changes are made to the orderline clicked on.
        PosSelf.check.isOrderline("Office Chair Black", "138.58", ""),
        ...PosSelf.action.editOrderline("Office Chair Black", "138.58", "", 5, "no wheels"),
        PosSelf.check.isOrderline("Office Chair Black", "692.90", "no wheels"),
        ...PosSelf.action.editOrderline("Office Chair Black", "692.90", "no wheels", -4, "kidding"),
        PosSelf.check.isOrderline("Office Chair Black", "138.58", "kidding"),
        PosSelf.action.clickBack(),

        // Once an order has been sent to the server, the user can no
        // longer reduce the quantity of his orderlines. We check this behaviour.
        PosSelf.action.clickPrimaryBtn("Review"),
        ...PosSelf.action.editOrderline("Large Cabinet", "736.00", "", -1),
        PosSelf.check.isOrderline("Large Cabinet", "368.00", ""),

        // Here we look at whether the user can reduce the quantity
        // and delete a product that has not yet been sent
        PosSelf.action.clickBack(),
        ...PosSelf.action.addProduct("Funghi", 1),
        PosSelf.action.clickPrimaryBtn("Review"),
        ...PosSelf.action.editOrderline("Funghi", "8.05", "", -1),
        PosSelf.check.isNotOrderline("Funghi", "8.05", ""),

        // Here we're looking at whether adding a product with the same description
        // as the same product already in the basket merges the two products.
        // We also check whether we can reduce the quantity of the part not yet sent to
        // the server and whether the quantity of the part sent to the server is fixed.
        PosSelf.action.clickBack(),
        ...PosSelf.action.addProduct("Office Chair Black", 1, "kidding"),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.check.isOrderline("Office Chair Black", "277.16", "kidding"),
        ...PosSelf.action.editOrderline("Office Chair Black", "277.16", "kidding", -1),
        PosSelf.check.isOrderline("Office Chair Black", "138.58", "kidding"),
        ...PosSelf.action.editOrderline("Office Chair Black", "138.58", "kidding", -1),
        PosSelf.check.isNotOrderline("Office Chair Black", "138.58", ""),
        PosSelf.action.clickBack(),

        // Here we check that the product attributes are correctly selected.
        ...PosSelf.action.addProduct("Desk Organizer", 1, "kidding", {
            radio: { name: "Size", value: "M" },
            select: { name: "Fabric", value: "Leather" },
        }),
        ...PosSelf.action.addProduct("Desk Organizer", 2, "okkk", {
            radio: { name: "Size", value: "L" },
            select: { name: "Fabric", value: "Custom" },
        }),
        PosSelf.action.clickPrimaryBtn("Review"),
        PosSelf.check.isOrderline("Desk Organizer", "5.87", "kidding", "M, Leather"),
        PosSelf.check.isOrderline("Desk Organizer", "11.74", "okkk", "L, Custom"),

        // Check if we can edit the product attributes, and if the changes are made to the orderline
        ...PosSelf.action.editOrderline("Desk Organizer", "5.87", "kidding", 0, "dav", {
            radio: { name: "Size", value: "S" },
            select: { name: "Fabric", value: "Custom" },
        }),
        PosSelf.check.isOrderline("Desk Organizer", "5.87", "dav", "S, Custom"),
        PosSelf.check.isOrderline("Desk Organizer", "11.74", "okkk", "L, Custom"),
        PosSelf.action.clickBack(),
    ],
});
