import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import { registry } from "@web/core/registry";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/tours/utils/product_configurator_util";
import { negateStep } from "@point_of_sale/../tests/tours/utils/common";

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Organizer", "2"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true),
            // Since the reward button is highlighted, clicking the reward product should be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer", "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            // In the succeeding 2 clicks on the product, it is considered as a regular product.
            // In the third click, the product will be added as reward.
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "6.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-10.20", "2.00"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("25.50"),
            // Finalize order that consumed a reward.
            PosLoyalty.finalizeOrder("Cash", "30"),

            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            ProductScreen.clickNumpad("9"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "9.00"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-15.30", "3.00"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.00"),
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
            ProductScreen.clickNumpad("6"),
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
            ProductScreen.clickNumpad("⌫"),
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
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad"),
            SelectionPopup.has("Desk Pad", { run: "click" }),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-1.98", "1.00"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad"),
            SelectionPopup.has("Monitor Stand", { run: "click" }),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Monitor Stand", "1.00", "3.19"),
            PosLoyalty.hasRewardLine("Free Product", "-3.19", "1.00"),
            PosLoyalty.orderTotalIs("4.81"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.addOrderline("Test Product A", "1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("Free Product - Test Product A", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product - Test Product A", "-11.50", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_free_product_rewards_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-5.10", "1.00"),
            PosLoyalty.orderTotalIs("10.20"),
            PosLoyalty.finalizeOrder("Cash", "10.20"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.selectedOrderlineHas("Test Product A", "1.00", "40.00"),
            ProductScreen.clickDisplayedProduct("Test Product B"),
            ProductScreen.selectedOrderlineHas("Test Product B", "1.00", "40.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 10 on specific products", "-10.00", "1.00"),
            PosLoyalty.orderTotalIs("70.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.orderTotalIs("60.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 30 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 30 on specific products", "-30.00", "1.00"),
            PosLoyalty.orderTotalIs("30.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithFreeProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickDisplayedProduct("Test Product C"),
            PosLoyalty.orderTotalIs("130.00"),
            PosLoyalty.isRewardButtonHighlighted(true, false),
            {
                content: `click Reward button`,
                trigger: ProductScreen.controlButtonTrigger("Reward"),
                run: "click",
            },
            Dialog.cancel(),
            PosLoyalty.orderTotalIs("130.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithRewardProductDomainTour", {
    steps: () =>
        [
            // Steps to check if the alert dialog for invalid domain loyalty program is present, only then will the pos screen load correctly
            Dialog.is("A reward could not be loaded"),
            Dialog.confirm("Ok"),

            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.selectedOrderlineHas("Product A", "1.00", "15.00"),
            PosLoyalty.orderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.selectedOrderlineHas("Product B", "1.00", "50.00"),
            PosLoyalty.orderTotalIs("40.00"),

            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("10$ on your order - Product B - Saleable", { run: "click" }),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("10$ on your order - Product B - Not Saleable", { run: "click" }),
            PosLoyalty.orderTotalIs("30.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyRewardProductTag", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Product A, Product B]"),
            SelectionPopup.has("Product A", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-2", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Product A, Product B]"),
            SelectionPopup.has("Product B", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-5", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Product A, Product B]"),
            SelectionPopup.has("Product B", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-10", "2.00"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_on_order_with_fixed_tax", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.enterCode("563412"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.50"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_reward_with_variant", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            PosLoyalty.hasRewardLine("Free Product", "-10", "1.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_reward_line_free_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "-10", "1.00"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("Free Product - Product B").map(negateStep),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "-5", "1.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "-10", "1.00"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "-5", "1.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "-10", "1.00"),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "-5", "1.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "-20", "2.00"),
        ].flat(),
});
