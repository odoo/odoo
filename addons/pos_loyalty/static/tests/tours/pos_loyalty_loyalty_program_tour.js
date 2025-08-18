import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as combo from "@point_of_sale/../tests/tours/utils/combo_popup_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

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
    steps: () =>
        [
            // Order1: Immediately set the customer to Test Partner AAA which has 4 points.
            // - He has enough points to purchase a free product but since there is still
            //   no product in the order, reward button should not yet be highlighted.
            // - Furthermore, clicking the reward product should not add it as reward product.
            Chrome.startPoS(),
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

registry.category("web_tour.tours").add("PosLoyaltyChangeRewardQty", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("DDD Test Partner"),
            ProductScreen.clickCustomer("DDD Test Partner"),
            ProductScreen.addOrderline("Desk Organizer", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            ProductScreen.clickNumpad("Qty"),
            ProductScreen.clickNumpad("1"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Generates 10.2 points and use points to get the reward product with zero sale price
            ProductScreen.addOrderline("Desk Organizer", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-1.00", "1.00"),

            PosLoyalty.orderTotalIs("10.2"),
            PosLoyalty.finalizeOrder("Cash", "10.2"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPromotion", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.addOrderline("Test Product 1", "1.00", "100"),
            ProductScreen.totalAmountIs("90.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyDontGrantPointsForRewardOrderLines", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner"),

            ProductScreen.addOrderline("Desk Organizer", "1"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("100% on the cheapest product"),

            PosLoyalty.orderTotalIs("5.10"),
            PosLoyalty.finalizeOrder("Cash", "5.10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyNextOrderCouponExpirationDate", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Organizer", "3"),

            PosLoyalty.finalizeOrder("Cash", "15.3"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosComboCheapestRewardProgram", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Expensive product"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            inLeftSide(Order.hasLine({ productName: "10% on the cheapest product" })),
            PosLoyalty.orderTotalIs("1,204.25"),
            PosLoyalty.finalizeOrder("Cash", "1204.25"),
            ProductScreen.clickDisplayedProduct("Cheap product"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Order.hasLine({ productName: "10% on the cheapest product" }),
            PosLoyalty.orderTotalIs("61.03"),
            PosLoyalty.finalizeOrder("Cash", "61.03"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosComboSpecificProductProgram", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Order.hasLine({ productName: "10% on Office Combo" }),
            PosLoyalty.orderTotalIs("216.00"),
            PosLoyalty.finalizeOrder("Cash", "216.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosCheapestProductTaxInclude", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product"),
            ProductScreen.addOrderline("Desk Organizer", "1"),
            Order.hasLine({ productName: "10% on the cheapest product" }),
            PosLoyalty.orderTotalIs("6.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_not_create_loyalty_card_expired_program", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            PosLoyalty.finalizeOrder("Cash", "15.3"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosOrderClaimReward", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            PosLoyalty.isPointsDisplayed(true),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            PosLoyalty.finalizeOrder("Cash", "15.3"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosOrderNoPoints", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner 2"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            PosLoyalty.isPointsDisplayed(false),
            PosLoyalty.finalizeOrder("Cash", "15.3"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyMultipleOrders", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Order1: Add a product and leave the order in draft.
            ProductScreen.addOrderline("Whiteboard Pen", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),

            // Order2: Finalize a different order.
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Organizer", "1"),
            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_combo_product_dont_grant_point", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Order.hasLine({ productName: "100% on the cheapest product" }),
            ProductScreen.totalAmountIs("50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_buy_x_get_y_reward_qty", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "10"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-3.20", "1.00"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-6.40", "2.00"),
            PosLoyalty.finalizeOrder("Cash", "32"),
            ProductScreen.addOrderline("Whiteboard Pen", "10"),
            PosLoyalty.claimReward("Free Product - Whiteboard Pen"),
            PosLoyalty.hasRewardLine("Free Product - Whiteboard Pen", "-9.60", "3.00"),
            PosLoyalty.finalizeOrder("Cash", "32"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_max_usage_partner_with_point", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner 2"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            PosLoyalty.claimReward("100% on your order"),
            PosLoyalty.finalizeOrder("Cash", "0"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner 3"),
            ProductScreen.addOrderline("Desk Organizer", "3"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});
