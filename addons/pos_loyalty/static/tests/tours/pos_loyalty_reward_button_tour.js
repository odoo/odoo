import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Organizer", "2"),
            PosLoyalty.claimReward('Add "Free Product - Desk Organizer"'),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "1"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            // After adding the next line we should have 4 Desk Organizers, and 2 free
            ProductScreen.selectedOrderlineHas("Desk Organizer", "4"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "2"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("25.50"),
            // Finalize order that consumed a reward.
            PosLoyalty.finalizeOrder("Cash", "30"),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.claimReward('Add "Free Product - Desk Organizer"'),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "1"),
            ProductScreen.clickOrderline("Desk Organizer", "2"),
            ProductScreen.clickNumpad("9"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "9"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "4"),
            ProductScreen.clickLine("Free Product - Desk Organizer", "4"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "9"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Finalize order but without the reward.
            // This step is important. When syncing the order, no reward should be synced.
            PosLoyalty.orderTotalIs("10.20"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "2"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward('Add "Free Product - Whiteboard Pen"'),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "0", "1"),
            ProductScreen.clickOrderline("Magnetic Board", "3"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "3"),
            ProductScreen.clickNumpad("6"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "6"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "0", "2"),
            // Finalize order that consumed a reward.
            PosLoyalty.orderTotalIs("11.88"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            ProductScreen.addOrderline("Magnetic Board", "6"),
            PosLoyalty.claimReward('Add "Free Product - Whiteboard Pen"'),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "0", "2"),
            PosLoyalty.isRewardButtonHighlighted(false),

            ProductScreen.clickOrderline("Magnetic Board", "6"),
            ProductScreen.clickNumpad("⌫"),
            // At this point, the reward should have been removed.
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "0"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "1"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "2"),
            ProductScreen.clickDisplayedProduct("Magnetic Board"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "3"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "0", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),

            PosLoyalty.orderTotalIs("5.94"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Promotion: 2 items of shelves, get desk_pad/monitor_stand free
            // This is the 5th order.
            ProductScreen.clickDisplayedProduct("Wall Shelf Unit"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Small Shelf"),
            ProductScreen.selectedOrderlineHas("Small Shelf", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Click reward product. Should be automatically added as reward.
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.hasRewardLine("Free Product - Desk Pad", "0", "1"),
            // Remove the reward line. The next steps will check if cashier
            // can select from the different reward products.
            ProductScreen.clickNumpad("⌫"),
            Dialog.isNot(),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Monitor Stand"),
            SelectionPopup.has("Desk Pad", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Desk Pad", "0", "1"),
            ProductScreen.clickNumpad("⌫"),
            Dialog.isNot(),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Desk Pad, Monitor Stand]"),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Desk Pad"),
            SelectionPopup.has("Monitor Stand", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Free Product - Monitor Stand", "1", "0"),
            PosLoyalty.orderTotalIs("6.79"),
            PosLoyalty.finalizeOrder("Cash", "10"),
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
            PosLoyalty.claimReward('Add "Free Product - Desk Organizer"'),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "1.00"),
            PosLoyalty.orderTotalIs("15.30"),
            PosLoyalty.finalizeOrder("Cash", "15.30"),
        ].flat(),
});
