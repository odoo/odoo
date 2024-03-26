/** @odoo-module **/

import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram1", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Order1: Generates 2 points.
            ProductScreen.addOrderline("Whiteboard Pen", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            PosLoyalty.orderTotalIs("6.40"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Order2: Consumes points to get free product.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "2.00"),
            // At this point, AAA Test Partner has 4 points.
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "3.00"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("6.40"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Order3: Generate 4 points.
            // - Initially gets free product, but was removed automatically by changing the
            //   number of items to zero.
            // - It's impossible to checked here if the free product reward is really removed
            //   so we check in the backend the number of orders that consumed the reward.
            ProductScreen.addOrderline("Whiteboard Pen", "4"),
            PosLoyalty.orderTotalIs("12.80"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickNumpad("⌫"),
            // At this point, the reward line should have been automatically removed
            // because there is not enough points to purchase it. Unfortunately, we
            // can't check that here.
            PosLoyalty.orderTotalIs("0.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "2.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "3.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.selectedOrderlineHas("Whiteboard Pen", "4.00"),
            PosLoyalty.isRewardButtonHighlighted(true),

            PosLoyalty.orderTotalIs("12.80"),
            PosLoyalty.finalizeOrder("Cash", "20"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram2", {
    test: true,
    steps: () =>
        [
            // Order1: Immediately set the customer to Test Partner AAA which has 4 points.
            // - He has enough points to purchase a free product but since there is still
            //   no product in the order, reward button should not yet be highlighted.
            // - Furthermore, clicking the reward product should not add it as reward product.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            // No item in the order, so reward button is off.
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("3.20"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Order2: Generate 4 points for CCC Test Partner.
            // - Reference: Order2_CCC
            // - But set BBB Test Partner first as the customer.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBB Test Partner"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "1.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "2.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "3.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "4.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("CCC Test Partner"),
            PosLoyalty.customerIs("CCC Test Partner"),
            PosLoyalty.orderTotalIs("12.80"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // Order3: Generate 3 points for BBB Test Partner.
            // - Reference: Order3_BBB
            // - But set CCC Test Partner first as the customer.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("CCC Test Partner"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.addOrderline("Whiteboard Pen", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("BBB Test Partner"),
            PosLoyalty.customerIs("BBB Test Partner"),
            PosLoyalty.orderTotalIs("9.60"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            // Order4: Should not have reward because the customer will be removed.
            // - Reference: Order4_no_reward
            ProductScreen.clickDisplayedProduct("Whiteboard Pen", true, "1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("CCC Test Partner"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            ProductScreen.clickPartnerButton(),
            // This deselects the customer.
            PosLoyalty.unselectPartner(),
            PosLoyalty.customerIs("Customer"),
            PosLoyalty.orderTotalIs("6.40"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram3", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Generates 10.2 points and use points to get the reward product with zero sale price
            ProductScreen.addOrderline("Desk Organizer", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-1.00", "1.00"),

            PosLoyalty.orderTotalIs("10.2"),
            PosLoyalty.finalizeOrder("Cash", "10.2"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPromotion", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.addOrderline("Test Product 1", "1.00", "100"),
            ProductScreen.totalAmountIs("80.00"),
        ].flat(),
});
