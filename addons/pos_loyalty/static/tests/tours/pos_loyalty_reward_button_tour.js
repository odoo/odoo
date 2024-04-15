/** @odoo-module **/

import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.addOrderline("Desk Organizer", "2"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.checkRewardButtonHighlighted(true),
            // Since the reward button is highlighted, clicking the reward product should be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer", "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            // In the succeeding 2 clicks on the product, it is considered as a regular product.
            // In the third click, the product will be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "6.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-10.20", "2.00"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            PosLoyalty.checkOrderTotalIs("25.50"),
            // Finalize order that consumed a reward.
            PosLoyalty.finalizeOrder("Cash", "30"),

            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.checkSelectedOrderlineHas("Desk Organizer", "0.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.00"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            // Finalize order but without the reward.
            // This step is important. When syncing the order, no reward should be synced.
            PosLoyalty.checkOrderTotalIs("10.20"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "2"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            ProductScreen.clickOrderline("Magnetic Board", "3.00"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "3.00"),
            ProductScreen.clickNumpad("6"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "6.00"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-6.40", "2.00"),
            // Finalize order that consumed a reward.
            PosLoyalty.checkOrderTotalIs("11.88"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "6"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.checkRewardButtonHighlighted(true),

            ProductScreen.clickOrderline("Magnetic Board", "6.00"),
            ProductScreen.clickNumpad("⌫"),
            // At this point, the reward should have been removed.
            PosLoyalty.checkRewardButtonHighlighted(false),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "0.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "1.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "2.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.checkSelectedOrderlineHas("Magnetic Board", "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.checkRewardButtonHighlighted(false),

            PosLoyalty.checkOrderTotalIs("5.94"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Promotion: 2 items of shelves, get desk_pad/monitor_stand free
            // This is the 5th order.
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.checkSelectedOrderlineHas("Wall Shelf Unit", "1.00"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.checkSelectedOrderlineHas("Small Shelf", "1.00"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            // Click reward product. Should be automatically added as reward.
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            PosLoyalty.checkRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-1.98", "1.00"),
            // Remove the reward line. The next steps will check if cashier
            // can select from the different reward products.
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad"),
            SelectionPopup.has("Desk Pad", { run: "click" }),
            PosLoyalty.checkRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-1.98", "1.00"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad"),
            SelectionPopup.has("Monitor Stand", { run: "click" }),
            PosLoyalty.checkRewardButtonHighlighted(false),
            ProductScreen.checkSelectedOrderlineHas("Monitor Stand", "1.00", "3.19"),
            PosLoyalty.hasRewardLine("Free Product", "-3.19", "1.00"),
            PosLoyalty.checkOrderTotalIs("4.81"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour2", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.addOrderline("Test Product A", "1"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("Free Product - Test Product A", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product - Test Product A", "-11.50", "1.00"),
            PosLoyalty.checkRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.checkSelectedOrderlineHas("Test Product A", "1.00", "40.00"),
            ProductScreen.clickDisplayedProduct("Test Product B"),
            ProductScreen.checkSelectedOrderlineHas("Test Product B", "1.00", "40.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 10 on specific products", "-10.00", "1.00"),
            PosLoyalty.checkOrderTotalIs("60.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithFreeProductTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickDisplayedProduct("Test Product C"),
            PosLoyalty.checkOrderTotalIs("130.00"),
            PosLoyalty.checkRewardButtonHighlighted(true),
            ProductScreen.clickControlButton("Reward"),
            Dialog.cancel(),
            PosLoyalty.checkOrderTotalIs("130.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithRewardProductDomainTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.checkSelectedOrderlineHas("Product A", "1.00", "15.00"),
            PosLoyalty.checkOrderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.checkSelectedOrderlineHas("Product B", "1.00", "50.00"),
            PosLoyalty.checkOrderTotalIs("40.00"),
        ].flat(),
});
