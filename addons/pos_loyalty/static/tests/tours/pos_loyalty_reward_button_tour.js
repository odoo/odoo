import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Awesome Item", "2"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true),
            // Since the reward button is highlighted, clicking the reward product should be added as reward.
            ProductScreen.clickDisplayedProduct("Awesome Item", "3"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            // In the succeeding 2 clicks on the product, it is considered as a regular product.
            // In the third click, the product will be added as reward.
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "6"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-200", "2"),

            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("500"),
            // Finalize order that consumed a reward.
            PosLoyalty.finalizeOrder("Cash", "500"),

            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "2"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "0"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "2"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Finalize order but without the reward.
            // This step is important. When syncing the order, no reward should be synced.
            PosLoyalty.orderTotalIs("200"),
            PosLoyalty.finalizeOrder("Cash", "200"),

            ProductScreen.addOrderline("Awesome Thing", "2"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Quality Thing"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Quality Thing", "-50", "1"),
            ProductScreen.clickOrderline("Awesome Thing", "3"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "3"),
            ProductScreen.clickNumpad("6"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "6"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Quality Thing"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product - Quality Thing", "-100", "2"),
            // Finalize order that consumed a reward.
            PosLoyalty.orderTotalIs("600"),
            PosLoyalty.finalizeOrder("Cash", "600"),

            ProductScreen.addOrderline("Awesome Thing", "6"),
            ProductScreen.clickDisplayedProduct("Quality Thing"),
            PosLoyalty.hasRewardLine("Free Product - Quality Thing", "-50", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),

            ProductScreen.clickOrderline("Awesome Thing", "6"),
            ProductScreen.clickNumpad("⌫"),
            // At this point, the reward should have been removed.
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "0"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "1"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "2"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "3"),
            PosLoyalty.hasRewardLine("Free Product - Quality Thing", "-50", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),

            PosLoyalty.orderTotalIs("300"),
            PosLoyalty.finalizeOrder("Cash", "300"),

            // Promotion: 2 items of shelves, get desk_pad/monitor_stand free
            // This is the 5th order.
            ProductScreen.clickDisplayedProduct("Quality Thing"),
            ProductScreen.selectedOrderlineHas("Quality Thing", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Quality Article"),
            ProductScreen.selectedOrderlineHas("Quality Article", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            // Click reward product. Should be automatically added as reward.
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-100", "1"),
            // Remove the reward line. The next steps will check if cashier
            // can select from the different reward products.
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Awesome Item, Awesome Article]"),
            SelectionPopup.has("Awesome Item"),
            SelectionPopup.has("Awesome Article"),
            SelectionPopup.has("Awesome Article", { run: "click" }),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.hasRewardLine("Free Product", "-100", "1"),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - [Awesome Item, Awesome Article]"),
            SelectionPopup.has("Awesome Item"),
            SelectionPopup.has("Awesome Article"),
            SelectionPopup.has("Awesome Item", { run: "click" }),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100"),
            PosLoyalty.hasRewardLine("Free Product", "-100", "1"),
            PosLoyalty.orderTotalIs("100"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyFreeProductTour2", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("Free Product - Awesome Item", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.selectedOrderlineHas("Awesome Article", "1", "100.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 10 on specific products", "-10.00", "1"),
            PosLoyalty.orderTotalIs("190.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 10 on specific products", { run: "click" }),
            PosLoyalty.orderTotalIs("180.00"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 30 on specific products", { run: "click" }),
            PosLoyalty.hasRewardLine("$ 30 on specific products", "-30.00", "1"),
            PosLoyalty.orderTotalIs("150.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithFreeProductTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.orderTotalIs("190.00"),
            PosLoyalty.isRewardButtonHighlighted(true, false),
            {
                content: `click Reward button`,
                trigger: ProductScreen.controlButtonTrigger("Reward"),
                run: "click",
            },
            Dialog.cancel(),
            PosLoyalty.orderTotalIs("190.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountWithRewardProductDomainTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "1", "100.00"),
            PosLoyalty.orderTotalIs("100.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyRewardProductTag", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Awesome Item, Awesome Article]"),
            SelectionPopup.has("Awesome Item", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-2", "1"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Awesome Item, Awesome Article]"),
            SelectionPopup.has("Awesome Article", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-5", "1"),
            PosLoyalty.isRewardButtonHighlighted(false, true),

            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - [Awesome Item, Awesome Article]"),
            SelectionPopup.has("Awesome Article", { run: "click" }),
            PosLoyalty.hasRewardLine("Free Product", "-10", "2"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
        ].flat(),
});
