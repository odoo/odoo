import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Notification from "@point_of_sale/../tests/generic_helpers/notification_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("PosLoyaltyTour1", {
    steps: () =>
        [
            // --- PoS Loyalty Tour Basic Part 1 ---
            // Generate coupons for PosLoyaltyTour2.

            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // basic order
            // just accept the automatically applied promo program
            // applied programs:
            //   - on cheapest product
            ProductScreen.addOrderline("Awesome Item", "5"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            PosLoyalty.selectRewardLine("on the cheapest product"),
            PosLoyalty.orderTotalIs("410"),
            PosLoyalty.finalizeOrder("Cash", "410"),

            // remove the reward from auto promo program
            // no applied programs
            ProductScreen.addOrderline("Awesome Item", "6"),
            PosLoyalty.hasRewardLine("on the cheapest product", "90"),
            PosLoyalty.orderTotalIs("510"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.orderTotalIs("600"),
            PosLoyalty.finalizeOrder("Cash", "600"),

            // order with coupon code from coupon program
            // applied programs:
            //   - coupon program
            ProductScreen.addOrderline("Awesome Article", "9"),
            PosLoyalty.hasRewardLine("on the cheapest product", "-90"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.orderTotalIs("900"),
            PosLoyalty.enterCode("invalid_code"),
            Notification.has("invalid_code"),
            PosLoyalty.enterCode("1234"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Article", "-300"),
            PosLoyalty.finalizeOrder("Cash", "600"),

            // Use coupon but eventually remove the reward
            // applied programs:
            //   - on cheapest product
            ProductScreen.addOrderline("Quality Thing", "4"), // 200
            ProductScreen.addOrderline("Awesome Article", "9"), // 900
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-45"),
            PosLoyalty.orderTotalIs("1,055"),
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Article", "-300"),
            PosLoyalty.orderTotalIs("755"),
            PosLoyalty.removeRewardLine("Free Product"),
            PosLoyalty.orderTotalIs("1,055"),
            PosLoyalty.finalizeOrder("Cash", "1055"),

            // specific product discount
            // applied programs:
            //   - on cheapest product
            //   - on specific products
            ProductScreen.addOrderline("Quality Item", "10"), // 500
            ProductScreen.addOrderline("Awesome Article", "3"), // 300
            ProductScreen.addOrderline("Awesome Thing", "4"), // 400 with 10% tax
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-45"),
            PosLoyalty.orderTotalIs("1,155"),
            PosLoyalty.enterCode("promocode"),
            PosLoyalty.hasRewardLine("50% on specific products", "-200"), // Awesome Thing
            PosLoyalty.hasRewardLine("50% on specific products", "-150"), // Awesome Article
            PosLoyalty.orderTotalIs("805.00"),
            PosLoyalty.finalizeOrder("Cash", "805.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour2", {
    steps: () =>
        [
            // --- PoS Loyalty Tour Basic Part 2 ---
            // Using the coupons generated from PosLoyaltyTour1.

            // Test that global discount and cheapest product discounts can be accumulated.
            // Applied programs:
            //   - global discount
            //   - on cheapest discount
            Chrome.startPoS(),
            ProductScreen.addOrderline("Awesome Article", "10"), // 1000
            PosLoyalty.hasRewardLine("on the cheapest product", "-90"),
            ProductScreen.addOrderline("Awesome Thing", "4"), // 400 with 10% tax
            PosLoyalty.hasRewardLine("on the cheapest product", "-90"),
            PosLoyalty.enterCode("123456"),
            PosLoyalty.hasRewardLine("10% on your order", "-40"),
            PosLoyalty.hasRewardLine("10% on your order", "-91"),
            PosLoyalty.orderTotalIs("1,179"), //SUBTOTAL
            PosLoyalty.finalizeOrder("Cash", "1179"),

            // Scanning coupon twice.
            // Also apply global discount on top of free product to check if the
            // calculated discount is correct.
            // Applied programs:
            //  - coupon program (free product)
            //  - global discount
            //  - on cheapest discount
            ProductScreen.addOrderline("Awesome Article", "11"), // 1100
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            PosLoyalty.orderTotalIs("1,010"),
            // add global discount and the discount will be replaced
            PosLoyalty.enterCode("345678"),
            PosLoyalty.hasRewardLine("10% on your order", "-101"),
            // add free product coupon (for qty=11, free=4)
            // the discount should change after having free products
            // it should go back to cheapest discount as it is higher
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Article", "-400"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            // set quantity to 18
            // free qty stays the same since the amount of points on the card only allows for 4 free products
            //TODO: The following step should works with ProductScreen.clickNumpad("⌫", "8"),
            ProductScreen.clickNumpad("⌫", "⌫", "1", "8"),
            PosLoyalty.hasRewardLine("10% on your order", "-131"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Article", "-400"),
            // scan the code again and check notification
            PosLoyalty.enterCode("5678"),
            PosLoyalty.orderTotalIs("1,179"),
            PosLoyalty.finalizeOrder("Cash", "1179"),

            // Specific products discount (with promocode) and free product (1357)
            // Applied programs:
            //   - discount on specific products
            //   - free product
            ProductScreen.addOrderline("Awesome Article", "6"), // 600
            PosLoyalty.hasRewardLine("on the cheapest product", "-90"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.enterCode("promocode"),
            PosLoyalty.hasRewardLine("50% on specific products", "-300"),
            PosLoyalty.enterCode("1357"),
            PosLoyalty.hasRewardLine("Free Product - Awesome Article", "-200"),
            PosLoyalty.hasRewardLine("50% on specific products", "-200"),
            PosLoyalty.orderTotalIs("200"),
            PosLoyalty.finalizeOrder("Cash", "200"),

            // Check reset program
            // Enter two codes and reset the programs.
            // The codes should be checked afterwards. They should return to new.
            // Applied programs:
            //   - cheapest product
            ProductScreen.addOrderline("Awesome Item", "6"), // 600
            PosLoyalty.enterCode("098765"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            PosLoyalty.hasRewardLine("10% on your order", "-51"),
            PosLoyalty.orderTotalIs("459"), // 600 - 90 - 51 = 459
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.hasRewardLine("10% on your order", "-60"),
            PosLoyalty.orderTotalIs("540"), // 600 - 60 = 540
            ProductScreen.clickControlButton("Reset Programs"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            PosLoyalty.orderTotalIs("510"),
            PosLoyalty.finalizeOrder("Cash", "510"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.orderTotalIs("105"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            PosLoyalty.hasRewardLine("100% on Awesome Thing", "-40"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour4", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Awesome Article", "1"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            ProductScreen.clickPriceList("Public Pricelist"),
            PosLoyalty.enterCode("abcda"),
            PosLoyalty.orderTotalIs("0.00"),
            ProductScreen.clickPriceList("Test multi-currency"),
            PosLoyalty.orderTotalIs("0.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosCouponTour5", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "1", "100"),
            PosLoyalty.clickDiscountButton(),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("80.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour7", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            PosLoyalty.orderTotalIs("100"),
            PosLoyalty.enterCode("abcda"),
            PosLoyalty.orderTotalIs("90"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour8", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountCategoryTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1", "100.00"),
            PosLoyalty.orderTotalIs("100.00"),
            ProductScreen.clickDisplayedProduct("Awesome Thing", true, "1", "100.00"),
            PosLoyalty.orderTotalIs("150.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour9", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.totalAmountIs("200.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("$ 5"),
            ProductScreen.totalAmountIs("195.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour10", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.customerIs("Partner One"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.totalAmountIs("1.00"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Awesome Article"),
            {
                content: `click on reward item`,
                trigger: `.selection-item:contains("Awesome Article")`,
                run: "click",
            },
            PosLoyalty.hasRewardLine("Free Product", "-1.00"),
            ProductScreen.totalAmountIs("1.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour11.1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.customerIs("Partner One"),
            ProductScreen.addOrderline("Awesome Thing", "3"),
            ProductScreen.totalAmountIs("300.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.finalizeOrder("Cash", "300"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour11.2", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.customerIs("Partner One"),
            ProductScreen.clickDisplayedProduct("Awesome Thing"),
            ProductScreen.totalAmountIs("100.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.enterCode("123456"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product"),
            PosLoyalty.hasRewardLine("Free Product", "-3.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.totalAmountIs("100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyMinAmountAndSpecificProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.orderTotalIs("90.00"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.selectedOrderlineHas("Awesome Article", "1", "100.00"),
            PosLoyalty.orderTotalIs("190.00"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "2", "200.00"),
            PosLoyalty.orderTotalIs("280.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour12", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "2"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.totalAmountIs("2.00"),
            PosLoyalty.hasRewardLine("Free Product", "-1.00"),
            ProductScreen.addOrderline("Awesome Article", "2"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.totalAmountIs("12.00"),
            PosLoyalty.hasRewardLine("Free Product", "-5.00"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.selectedOrderlineHas("Awesome Article", "6"),
            ProductScreen.totalAmountIs("22.00"),
            PosLoyalty.hasRewardLine("Free Product", "-10.00"),
        ].flat(),
});

function createOrderCoupon(totalAmount, couponName, couponAmount, loyaltyPoints) {
    return [
        Chrome.startPoS(),
        Dialog.confirm("Open Register"),
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer("Partner One"),
        ProductScreen.addOrderline("Awesome Item", "1"),
        ProductScreen.addOrderline("Awesome Article", "1"),
        PosLoyalty.enterCode("promocode"),
        PosLoyalty.hasRewardLine(`${couponName}`, `${couponAmount}`),
        PosLoyalty.orderTotalIs(`${totalAmount}`),
        PosLoyalty.pointsAwardedAre(`${loyaltyPoints}`),
        PosLoyalty.finalizeOrder("Cash", `${totalAmount}`),
    ].flat();
}

registry.category("web_tour.tours").add("PosLoyaltyPointsDiscountNoDomainProgramNoDomain", {
    steps: () => [createOrderCoupon("135.00", "10% on your order", "-15.00", "135")].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsDiscountNoDomainProgramDomain", {
    steps: () => [createOrderCoupon("135.00", "10% on your order", "-15.00", "100")].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsDiscountWithDomainProgramDomain", {
    steps: () => [createOrderCoupon("140.00", "10% on food", "-10.00", "90")].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsGlobalDiscountProgramNoDomain", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.hasRewardLine("10% on your order", "-10.00"),
            PosLoyalty.orderTotalIs("90"),
            PosLoyalty.pointsAwardedAre("90"),
            PosLoyalty.finalizeOrder("Cash", "90"),
        ].flat(),
});

registry.category("web_tour.tours").add("ChangeRewardValueWithLanguage", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.selectedOrderlineHas("Awesome Article", "1", "100.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("$ 2 on your order"),
            PosLoyalty.hasRewardLine("$ 2 on your order", "-2.00"),
            PosLoyalty.orderTotalIs("98.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyArchivedRewardProductsInactive", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyArchivedRewardProductsActive", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("CustomerLoyaltyPointsDisplayed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            PosLoyalty.orderTotalIs("100.00"),
            PosLoyalty.pointsAwardedAre("100"),
            PosLoyalty.finalizeOrder("Cash", "100.00"),
            PosLoyalty.checkPartnerPoints("Partner One", "100.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyalty2DiscountsSpecificGlobal", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.addOrderline("Awesome Item", "5"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.hasRewardLine("10% on your order", "-54.00"),
            PosLoyalty.hasRewardLine("10% on Awesome Item", "-60.00"),
            PosLoyalty.finalizeOrder("Cash", "486.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRewardProductScan", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            scan_barcode("95412427100283"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.hasRewardLine("50% on your order", "-50.00"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRewardProductScanGS1", {
    steps: () =>
        [
            Chrome.startPoS(),
            scan_barcode("0195412427100283"),
            ProductScreen.selectedOrderlineHas("Awesome Item", "1", "100.00"),
            PosLoyalty.hasRewardLine("50% on your order", "-50.00"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPromocodePricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Awesome Item", "1"),
            PosLoyalty.enterCode("hellopromo"),
            PosLoyalty.orderTotalIs("22.50"),
        ].flat(),
});

registry.category("web_tour.tours").add("RefundRulesProduct", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Item"),
            PosLoyalty.finalizeOrder("Cash", "100"),
            ProductScreen.isShown(),
            ...ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
        ].flat(),
});
