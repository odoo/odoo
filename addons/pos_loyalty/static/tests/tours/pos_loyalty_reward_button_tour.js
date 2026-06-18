import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";

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
            PosLoyalty.hasRewardLine("Free Product - Test Product A", "0", "1"),
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
            PosLoyalty.claimReward('Add "Free Product - Desk Organizer"'),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "0", "1.00"),
            PosLoyalty.orderTotalIs("15.30"),
            PosLoyalty.finalizeOrder("Cash", "15.30"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.selectedOrderlineHas("Test Product A", "1", "40.00"),
            ProductScreen.clickDisplayedProduct("Test Product B"),
            ProductScreen.selectedOrderlineHas("Test Product B", "1", "40.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 10 on specific products", "-10.00", "1"),
            PosLoyalty.orderTotalIs("70.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 30 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 30 on specific products", "-30.00", "1"),
            PosLoyalty.orderTotalIs("40.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithFreeProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickDisplayedProduct("Test Product C"),
            PosLoyalty.hasRewardLine("10% on Test Product C", "-10.00", "1"),
            PosLoyalty.claimReward('Add "Free Product - Test Product B"'),
            PosLoyalty.hasRewardLine("Free Product - Test Product B", "0.00", "1"),
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
            ProductScreen.selectedOrderlineHas("Product A", "1", "15.00"),
            PosLoyalty.orderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.selectedOrderlineHas("Product B", "1", "50.00"),
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
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Product B"),
            SelectionPopup.has("Product A", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.hasRewardLine("Free Product - Product A", "0.00", "1"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "0.00", "2"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
            PosLoyalty.selectRewardLine("Free Product - Product A"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.doesNotHaveRewardLine("Free Product - Product A"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Product A, Product B]"),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Product B", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.hasRewardLine("Free Product - Product B", "0.00", "2"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "0.00", "3"),
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
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("Test Partner", true),
            ProductScreen.clickCustomer("Test Partner"),
            ProductScreen.clickDisplayedProduct("Test Product"),
            Dialog.discard(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Test Product"),
            ProductConfiguratorPopup.pickRadio("Value 1"),
            Dialog.confirm(),
            PosLoyalty.claimReward(
                'Add "Free Product - [Test Product (Value 1), Test Product (Value 2)]"'
            ),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Test Product (Value 1)", { run: "click" }),
            Dialog.isNot(),
            ProductScreen.selectedOrderlineHas(
                "Free Product - Test Product (Value 1)",
                "1",
                "0",
                "Value 1"
            ),
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
            PosLoyalty.claimReward('Add "Free Product - Product A"'),
            ProductScreen.selectedOrderlineHas("Free Product - Product A", "1", "0"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ...PosLoyalty.selectRewardLine("Free Product - Product A"),
            ProductScreen.clickNumpad("1"),
            PosLoyalty.claimReward('Add "Free Product - Product B"'),
            PosLoyalty.hasRewardLine("Free Product - Product B"),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "0", "1.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "0", "1.00"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "0", "1.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "0", "1.00"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ...PosLoyalty.selectRewardLine("Free Product - Product A"),
            ProductScreen.clickNumpad("2"),
            PosLoyalty.hasRewardLine("Free Product - Product B", "0", "2.00"),
            PosLoyalty.hasRewardLine("Free Product - Product A", "0", "2.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_free_product_multiple_reward_products", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Promo Item A"),
            ProductScreen.clickDisplayedProduct("Promo Item B"),
            PosLoyalty.claimReward("Buy 2 Take 1"),
            Dialog.is({ title: "Please select a product for this reward" }),
            SelectionPopup.has("Promo Item A", { run: "click" }),
            Dialog.isNot(),
            PosLoyalty.hasRewardLine("Free Product", "0", "1"),
            ProductScreen.totalAmountIs("20.00"),
            // 6 products, the 2nd free product is claimed on another product than the reward line's one
            ProductScreen.clickDisplayedProduct("Promo Item A"),
            ProductScreen.clickDisplayedProduct("Promo Item A"),
            ProductScreen.selectedOrderlineHas("Promo Item A", "3.00"),
            PosLoyalty.hasRewardLine("Free Product", "0", "2"),
            ProductScreen.totalAmountIs("40.00"),
        ].flat(),
});
