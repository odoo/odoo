/** @odoo-module **/

import * as PosLoyalty from "@pos_loyalty/../tests/tours/PosLoyaltyTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as SelectionPopup from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.addOrderline("Desk Organizer", "2"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true),
            // Since the reward button is highlighted, clicking the reward product should be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            // In the succeeding 2 clicks on the product, it is considered as a regular product.
            // In the third click, the product will be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "6.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-10.20", "2.00"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("25.50"),
            // Finalize order that consumed a reward.
            PosLoyalty.finalizeOrder("Cash", "30"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "2.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "2.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Finalize order but without the reward.
            // This step is important. When syncing the order, no reward should be synced.
            PosLoyalty.orderTotalIs("10.20"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "2"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            ProductScreen.clickOrderline("Magnetic Board", "3.00"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "3.00"),
            ProductScreen.pressNumpad("6"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "6.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-6.40", "2.00"),
            // Finalize order that consumed a reward.
            PosLoyalty.orderTotalIs("11.88"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "6"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(true),

            ProductScreen.clickOrderline("Magnetic Board", "6.00"),
            ProductScreen.pressNumpad("⌫"),
            // At this point, the reward should have been removed.
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "0.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "1.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "2.00"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),

            PosLoyalty.orderTotalIs("5.94"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Promotion: 2 items of shelves, get desk_pad/monitor_stand free
            // This is the 5th order.
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.selectedOrderlineHas("Small Shelf", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Click reward product. Should be automatically added as reward.
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-1.98", "1.00"),
            // Remove the reward line. The next steps will check if cashier
            // can select from the different reward products.
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.pressNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.hasSelectionItem("Monitor Stand"),
            SelectionPopup.hasSelectionItem("Desk Pad"),
            SelectionPopup.clickItem("Desk Pad"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-1.98", "1.00"),
            ProductScreen.pressNumpad("⌫"),
            ProductScreen.pressNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.hasSelectionItem("Monitor Stand"),
            SelectionPopup.hasSelectionItem("Desk Pad"),
            SelectionPopup.clickItem("Monitor Stand"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.00", "3.19"),
            PosLoyalty.hasRewardLine("Free Product", "-3.19", "1.00"),
            PosLoyalty.orderTotalIs("4.81"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour2", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.addOrderline("Test Product A", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.clickRewardButton(),
            SelectionPopup.clickItem("Free Product - Test Product A"),
            PosLoyalty.hasRewardLine("Free Product - Test Product A", "-11.50", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.selectedOrderlineHas("Test Product A", "1.00", "40.00"),
            ProductScreen.clickDisplayedProduct("Test Product B"),
            ProductScreen.selectedOrderlineHas("Test Product B", "1.00", "40.00"),
            PosLoyalty.clickRewardButton(),
            SelectionPopup.clickItem("$ 10 per order on specific products"),
            PosLoyalty.hasRewardLine("$ 10 per order on specific products", "-10.00", "1.00"),
            PosLoyalty.orderTotalIs("70.00"),
            PosLoyalty.clickRewardButton(),
            SelectionPopup.clickItem("$ 10 per order on specific products"),
            PosLoyalty.orderTotalIs('60.00'),
            PosLoyalty.clickRewardButton(),
            SelectionPopup.clickItem("$ 30 per order on specific products"),
            PosLoyalty.hasRewardLine('$ 30 per order on specific products', '-30.00', '1.00'),
            PosLoyalty.orderTotalIs('30.00'),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithFreeProductTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickDisplayedProduct("Test Product C"),
            PosLoyalty.orderTotalIs("130.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.clickRewardButton(),
            PosLoyalty.orderTotalIs("130.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithRewardProductDomainTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00", "15.00"),
            PosLoyalty.orderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.selectedOrderlineHas("Product B", "1.00", "50.00"),
            PosLoyalty.orderTotalIs("40.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyRewardProductTag", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [product_a, product_b]"),
            SelectionPopup.clickItem("product_a"),
            PosLoyalty.hasRewardLine("Free Product", "-2", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [product_a, product_b]"),
            SelectionPopup.clickItem("product_b"),
            PosLoyalty.hasRewardLine("Free Product", "-5", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [product_a, product_b]"),
            SelectionPopup.clickItem("product_b"),
            PosLoyalty.hasRewardLine("Free Product", "-10", "2.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_on_order_with_fixed_tax", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.enterCode("563412"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.50"),
        ].flat(),
});
