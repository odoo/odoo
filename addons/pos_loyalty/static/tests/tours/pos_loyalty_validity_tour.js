/** @odoo-module **/

import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyValidity1", {
    test: true,
    steps: () =>
        [
            // First tour should not get any automatic rewards

            Dialog.confirm("Open session"),

            // Not valid -> date
            ProductScreen.addOrderline("Whiteboard Pen", "5"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("16.00"),
            PosLoyalty.finalizeOrder("Cash", "16"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyValidity2", {
    test: true,
    steps: () =>
        [
            // Second tour
            // Valid
            ProductScreen.addOrderline("Whiteboard Pen", "5"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-2.88"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // Not valid -> usage
            ProductScreen.addOrderline("Whiteboard Pen", "5"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("16.00"),
            PosLoyalty.finalizeOrder("Cash", "16.00"),
        ].flat(),
});
