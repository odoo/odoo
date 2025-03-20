import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Order1: Generates 2 points.
            ProductScreen.addOrderline("Awesome Item", "2"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.orderTotalIs("200"),
            PosLoyalty.finalizeOrder("Cash", "200"),

            // Order2: Consumes points to get free product.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "2"),
            // At this point, Partner One has 4 points.
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "3"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("200"),
            PosLoyalty.finalizeOrder("Cash", "200"),

            // Order3: Generate 4 points.
            // - Initially gets free product, but was removed automatically by changing the
            //   number of items to zero.
            // - It's impossible to checked here if the free product reward is really removed
            //   so we check in the backend the number of orders that consumed the reward.
            ProductScreen.addOrderline("Awesome Item", "4"),
            PosLoyalty.orderTotalIs("400"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickNumpad("⌫"),
            ProductScreen.clickNumpad("⌫"),
            // At this point, the reward line should have been automatically removed
            // because there is not enough points to purchase it. Unfortunately, we
            // can't check that here.
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.addOrderline("Awesome Item", "4"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "4"),
            PosLoyalty.isRewardButtonHighlighted(true),

            PosLoyalty.orderTotalIs("400"),
            PosLoyalty.finalizeOrder("Cash", "400"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram2", {
    steps: () =>
        [
            // Order1: Immediately set the customer to Test Partner One which has 4 points.
            // - He has enough points to purchase a free product but since there is still
            //   no product in the order, reward button should not yet be highlighted.
            // - Furthermore, clicking the reward product should not add it as reward product.
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            // No item in the order, so reward button is off.
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.orderTotalIs("100"),
            PosLoyalty.finalizeOrder("Cash", "100"),

            // Order2: Generate 4 points for Partner Three
            // - But set Partner Two first as the customer.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Two"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "2"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "3"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "4"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Three"),
            PosLoyalty.customerIs("Partner Three"),
            PosLoyalty.orderTotalIs("400"),
            PosLoyalty.finalizeOrder("Cash", "400"),

            // Order3: Generate 3 points for Partner Two
            // - But set Partner Three first as the customer.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Three"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.addOrderline("Awesome Item", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Two"),
            PosLoyalty.customerIs("Partner Two"),
            PosLoyalty.orderTotalIs("300"),
            PosLoyalty.finalizeOrder("Cash", "300"),

            // Order4: Should not have reward because the customer will be removed.
            // - Reference: Order4_no_reward
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Three"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Awesome Item"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
            ProductScreen.clickPartnerButton(),
            // This deselects the customer.
            PosLoyalty.unselectPartner(),
            PosLoyalty.customerIs("Customer"),
            PosLoyalty.orderTotalIs("200"),
            PosLoyalty.finalizeOrder("Cash", "200"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyChangeRewardQty", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            PartnerList.searchCustomerValue("Partner Four"),
            ProductScreen.clickCustomer("Partner Four"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product - Awesome Item"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-200", "2"),
            ProductScreen.clickNumpad("Qty"),
            ProductScreen.clickNumpad("1"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Item", "-100", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyLoyaltyProgram3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Generates 10.2 points and use points to get the reward product with zero sale price
            ProductScreen.addOrderline("Awesome Item", "5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),

            // At this point, the free_product program is triggered.
            // The reward button should be highlighted.
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("Free Product - Quality Item"),
            PosLoyalty.hasRewardLine("Free Product - Quality Item", "-50.00", "1"),
            PosLoyalty.orderTotalIs("5.00"),
            PosLoyalty.finalizeOrder("Cash", "5.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPromotion", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.addOrderline("Awesome Item", "1", "100"),
            ProductScreen.totalAmountIs("90.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyDontGrantPointsForRewardOrderLines", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.addOrderline("Awesome Article", "1"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("100% on the cheapest product"),
            PosLoyalty.orderTotalIs("100"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyNextOrderCouponExpirationDate", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "3"),
            PosLoyalty.finalizeOrder("Cash", "300"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosComboCheapestRewardProgram", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            inLeftSide(Order.hasLine({ productName: "10% on the cheapest product" })),
            PosLoyalty.orderTotalIs("1,054.25"),
            PosLoyalty.finalizeOrder("Cash", "1054.25"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 1"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            Order.hasLine({ productName: "10% on the cheapest product" }),
            PosLoyalty.orderTotalIs("60.90"),
            PosLoyalty.finalizeOrder("Cash", "60.90"),
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
            ProductScreen.addOrderline("Awesome Item", "1"),
            Order.hasLine({ productName: "10% on the cheapest product" }),
            PosLoyalty.orderTotalIs("2.88"),
        ].flat(),
});
