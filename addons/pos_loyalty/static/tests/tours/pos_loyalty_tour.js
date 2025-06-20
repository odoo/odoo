import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
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
            //   - on cheapest product (out of 2, so 5 products => 2 discounted, 6 ==> 3)
            ProductScreen.addOrderline("Whiteboard Pen", "5"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-5.76"),
            PosLoyalty.selectRewardLine("Buy 2, get 90% on the cheapest"),
            PosLoyalty.orderTotalIs("10.24"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // remove the reward from auto promo program
            // no applied programs
            ProductScreen.addOrderline("Whiteboard Pen", "6"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-8.64"),
            PosLoyalty.orderTotalIs("10.56"),
            PosLoyalty.removeRewardLine("Buy 2, get 90% on the cheapest"),
            PosLoyalty.orderTotalIs("19.2"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // order with coupon code from coupon program
            // applied programs:
            //   - coupon program
            ProductScreen.addOrderline("Desk Organizer", "9"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-18.36"),
            PosLoyalty.removeRewardLine("Buy 2, get 90% on the cheapest"),
            PosLoyalty.orderTotalIs("45.90"),
            PosLoyalty.enterCode("invalid_code"),
            Notification.has("invalid_code"),
            PosLoyalty.enterCode("1234"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-15.30"),
            PosLoyalty.finalizeOrder("Cash", "50"),

            // Use coupon but eventually remove the reward
            // applied programs:
            //   - on cheapest product (out of 2, so 4 products => 2 discounted, 9 ==> 4)
            ProductScreen.addOrderline("Letter Tray", "4"),
            ProductScreen.addOrderline("Desk Organizer", "9"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-9.50"), // tax 10%
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-18.36"), // no tax
            PosLoyalty.orderTotalIs("39.16"),
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-15.30"),
            PosLoyalty.orderTotalIs("23.86"),
            PosLoyalty.removeRewardLine("Free Product"),
            PosLoyalty.orderTotalIs("39.16"),
            PosLoyalty.finalizeOrder("Cash", "90"),

            // specific product discount
            // applied programs:
            //   - on cheapest product (out of 2, so 10 products => 5 discounted, 9 ==> 4)
            //   - on specific products
            ProductScreen.addOrderline("Magnetic Board", "10"), // 1.98 => subtotal 19.8
            ProductScreen.addOrderline("Desk Organizer", "3"), // 5.1 => subtotal 15.3
            ProductScreen.addOrderline("Letter Tray", "4"), // 4.8 tax 10% => subtotal 21.12
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-9.50"), // tax 10%
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-13.50"), // no tax
            PosLoyalty.orderTotalIs("33.22"),
            PosLoyalty.enterCode("promocode"),
            PosLoyalty.hasRewardLine("50% on specific products", "-10.80"), // (35.1 - 13.5) * .5
            PosLoyalty.orderTotalIs("22.42"),
            PosLoyalty.finalizeOrder("Cash", "50"),
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
            ProductScreen.addOrderline("Desk Organizer", "10"), // 5.1
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-22.95"),
            ProductScreen.addOrderline("Letter Tray", "4"), // 4.8 tax 10%
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-9.50"),
            PosLoyalty.enterCode("123456"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.17"),
            PosLoyalty.hasRewardLine("10% on your order", "-2.81"),
            PosLoyalty.orderTotalIs("35.69"), //SUBTOTAL
            PosLoyalty.finalizeOrder("Cash", "70"),

            // Scanning coupon twice.
            // Also apply global discount on top of free product to check if the
            // calculated discount is correct.
            // Applied programs:
            //  - coupon program (free product)
            //  - global discount
            //  - on cheapest discount
            ProductScreen.addOrderline("Desk Organizer", "11"), // 5.1 per item
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-22.95"),
            PosLoyalty.orderTotalIs("33.15"),
            // add global discount and the discount will be added
            PosLoyalty.enterCode("345678"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-22.95"),
            PosLoyalty.hasRewardLine("10% on your order", "-3.32"),
            // add free product coupon (for qty=11, free=4)
            // the discount should change after having free products
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-20.40"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-22.95"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.28"),
            // set quantity to 18
            // free qty stays the same since the amount of points on the card only allows for 4 free products
            //TODO: The following step should works with ProductScreen.clickNumpad("⌫", "8"),
            ProductScreen.clickNumpad("⌫", "⌫", "1", "8"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-20.40"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-41.31"),
            PosLoyalty.hasRewardLine("10% on your order", "-3.01"),
            // scan the code again and check notification
            PosLoyalty.enterCode("5678"),
            PosLoyalty.orderTotalIs("27.08"),
            PosLoyalty.finalizeOrder("Cash", "65"),

            // Specific products discount (with promocode) and free product (1357)
            // Applied programs:
            //   - discount on specific products
            //   - free product
            ProductScreen.addOrderline("Desk Organizer", "6"), // 5.1 per item
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-13.77"),
            PosLoyalty.removeRewardLine("Buy 2, get 90% on the cheapest"),
            PosLoyalty.enterCode("promocode"),
            PosLoyalty.hasRewardLine("50% on specific products", "-15.30"),
            PosLoyalty.enterCode("1357"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-10.20"),
            PosLoyalty.hasRewardLine("50% on specific products", "-10.20"),
            PosLoyalty.orderTotalIs("10.20"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // Check reset program
            // Enter two codes and reset the programs.
            // The codes should be checked afterwards. They should return to new.
            // Applied programs:
            //   - cheapest product
            ProductScreen.addOrderline("Monitor Stand", "6"), // 3.19 per item
            PosLoyalty.enterCode("098765"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-8.61"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.05"),
            PosLoyalty.orderTotalIs("9.48"),
            PosLoyalty.removeRewardLine("Buy 2, get 90% on the cheapest"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.91"),
            PosLoyalty.orderTotalIs("17.23"),
            ProductScreen.clickControlButton("Reset Programs"),
            PosLoyalty.hasRewardLine("Buy 2, get 90% on the cheapest", "-8.61"),
            PosLoyalty.orderTotalIs("10.53"),
            PosLoyalty.finalizeOrder("Cash", "20"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour3", {
    steps: () =>
        [
            // --- PoS Loyalty Tour Basic Part 3 ---

            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Promo Product"),
            PosLoyalty.orderTotalIs("34.50"),
            ProductScreen.clickDisplayedProduct("Product B"),
            PosLoyalty.hasRewardLine("100% on specific products", "25.00"),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.hasRewardLine("100% on specific products", "15.00"),
            PosLoyalty.orderTotalIs("34.50"),
            ProductScreen.clickDisplayedProduct("Product A"),
            PosLoyalty.hasRewardLine("100% on specific products", "21.82"),
            PosLoyalty.hasRewardLine("100% on specific products", "18.18"),
            PosLoyalty.orderTotalIs("49.50"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour4", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Test Product 1", "1"),
            ProductScreen.addOrderline("Test Product 2", "1"),
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
            ProductScreen.addOrderline("Test Product 1", "1", "100"),
            PosLoyalty.clickDiscountButton(),
            Dialog.confirm(),
            ProductScreen.totalAmountIs("92.00"),
        ].flat(),
});

//transform the last tour to match the new format
registry.category("web_tour.tours").add("PosLoyaltyTour6", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            PosLoyalty.checkAddedLoyaltyPoints("26.5"),
            ProductScreen.clickControlButton("Reward"),
            SelectionPopup.has("$ 1.00 per point on your order", { run: "click" }),
            ProductScreen.totalAmountIs("165.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour7", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Test Product", "1"),
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

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.totalAmountIs("50.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificDiscountCategoryTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Product A", true, "1", "15.00"),
            PosLoyalty.orderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B", true, "1", "50.00"),
            PosLoyalty.orderTotalIs("40.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour9", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.totalAmountIs("210.00"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("$ 5"),
            ProductScreen.totalAmountIs("205.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour10", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            PosLoyalty.customerIs("AAA Partner"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.totalAmountIs("1.00"),
            ProductScreen.selectedOrderlineHas("Product Test", "1"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product B"),
            {
                content: `click on reward item`,
                trigger: `.selection-item:contains("Free Product B")`,
                run: "click",
            },
            PosLoyalty.hasRewardLine("Free Product B", "-1.00"),
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
            ProductScreen.clickCustomer("AAA Partner"),
            PosLoyalty.customerIs("AAA Partner"),
            ProductScreen.addOrderline("Product Test", "3"),
            ProductScreen.totalAmountIs("150.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.finalizeOrder("Cash", "150"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour11.2", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Partner"),
            PosLoyalty.customerIs("AAA Partner"),
            ProductScreen.clickDisplayedProduct("Product Test"),
            ProductScreen.totalAmountIs("50.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            PosLoyalty.enterCode("123456"),
            PosLoyalty.isRewardButtonHighlighted(true),
            PosLoyalty.claimReward("Free Product"),
            PosLoyalty.hasRewardLine("Free Product", "-3.00"),
            PosLoyalty.isRewardButtonHighlighted(false),
            ProductScreen.totalAmountIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyMinAmountAndSpecificProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.selectedOrderlineHas("Product A", "1", "20.00"),
            PosLoyalty.orderTotalIs("20.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.selectedOrderlineHas("Product B", "1", "30.00"),
            PosLoyalty.orderTotalIs("50.00"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.selectedOrderlineHas("Product A", "2", "40.00"),
            PosLoyalty.orderTotalIs("66.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyTour12", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Free Product A", "2"),
            ProductScreen.clickDisplayedProduct("Free Product A"),
            ProductScreen.totalAmountIs("2.00"),
            PosLoyalty.hasRewardLine("Free Product", "-1.00"),
            ProductScreen.addOrderline("Free Product B", "2"),
            ProductScreen.clickDisplayedProduct("Free Product B"),
            ProductScreen.totalAmountIs("12.00"),
            PosLoyalty.hasRewardLine("Free Product", "-5.00"),
            ProductScreen.clickDisplayedProduct("Free Product B"),
            ProductScreen.clickDisplayedProduct("Free Product B"),
            ProductScreen.clickDisplayedProduct("Free Product B"),
            ProductScreen.selectedOrderlineHas("Free Product B", "6"),
            ProductScreen.totalAmountIs("22.00"),
            PosLoyalty.hasRewardLine("Free Product", "-10.00"),
        ].flat(),
});

function createOrderCoupon(totalAmount, couponName, couponAmount, loyaltyPoints) {
    return [
        Chrome.startPoS(),
        Dialog.confirm("Open Register"),
        ProductScreen.clickPartnerButton(),
        ProductScreen.clickCustomer("AAAA"),
        ProductScreen.addOrderline("product_a", "1"),
        ProductScreen.addOrderline("product_b", "1"),
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
            ProductScreen.addOrderline("product_a", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
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

            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1", "5.10"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("$ 2.00 on your order"),
            PosLoyalty.hasRewardLine("$ 2.00 on your order", "-2.00"),
            PosLoyalty.orderTotalIs("3.10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyArchivedRewardProductsInactive", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
            ProductScreen.selectedOrderlineHas("Test Product A", "1", "100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyArchivedRewardProductsActive", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            PosLoyalty.isRewardButtonHighlighted(true),
            ProductScreen.selectedOrderlineHas("Test Product A", "1", "100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("CustomerLoyaltyPointsDisplayed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("product_a"),
            ProductScreen.selectedOrderlineHas("product_a", "1", "100.00"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("John Doe"),

            PosLoyalty.orderTotalIs("100.00"),
            PosLoyalty.pointsAwardedAre("100"),
            PosLoyalty.finalizeOrder("Cash", "100.00"),

            PosLoyalty.checkPartnerPoints("John Doe", "100.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyalty2DiscountsSpecificGlobal", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),

            ProductScreen.addOrderline("Test Product A", "5"),
            ProductScreen.clickDisplayedProduct("Test Product B"),
            PosLoyalty.hasRewardLine("10% on your order", "-3.00"),
            PosLoyalty.hasRewardLine("10% on Test Product B", "-0.45"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltySpecificProductDiscountWithGlobalDiscount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product A", "1"),
            PosLoyalty.hasRewardLine("$ 40.00 on Product A", "-40.00"),
            PosLoyalty.clickDiscountButton(),
            Dialog.confirm(),
            PosLoyalty.hasRewardLine("$ 40.00 on Product A", "-40.00"),
            PosLoyalty.orderTotalIs("20.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRewardProductScan", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("95412427100283"),
            ProductScreen.selectedOrderlineHas("product_a", "1", "1,150.00"),
            PosLoyalty.hasRewardLine("50% on your order", "-575.00"),
            PosLoyalty.orderTotalIs("575.00"),
            PosLoyalty.finalizeOrder("Cash", "575.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosRewardProductScanGS1", {
    steps: () =>
        [
            Chrome.startPoS(),
            scan_barcode("0195412427100283"),
            ProductScreen.selectedOrderlineHas("product_a", "1", "1,150.00"),
            PosLoyalty.hasRewardLine("50% on your order", "-575.00"),
            PosLoyalty.orderTotalIs("575.00"),
            PosLoyalty.finalizeOrder("Cash", "575.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPromocodePricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Product 1", "1"),
            PosLoyalty.enterCode("hellopromo"),
            PosLoyalty.orderTotalIs("25.87"),
        ].flat(),
});

registry.category("web_tour.tours").add("RefundRulesProduct", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("product_a"),
            PosLoyalty.finalizeOrder("Cash", "1000"),
            ProductScreen.isShown(),
            ...ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_two_variant_same_discount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Sofa"),
            Chrome.clickBtn("Add"),
        ].flat(),
});
