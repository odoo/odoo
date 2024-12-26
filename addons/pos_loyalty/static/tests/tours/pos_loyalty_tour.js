import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Notification from "@point_of_sale/../tests/tours/utils/generic_components/notification_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/tours/utils/common";

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
            ProductScreen.addOrderline("Whiteboard Pen", "5"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-2.88"),
            PosLoyalty.selectRewardLine("on the cheapest product"),
            PosLoyalty.orderTotalIs("13.12"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // remove the reward from auto promo program
            // no applied programs
            ProductScreen.addOrderline("Whiteboard Pen", "6"),
            PosLoyalty.hasRewardLine("on the cheapest product", "-2.88"),
            PosLoyalty.orderTotalIs("16.32"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.orderTotalIs("19.2"),
            PosLoyalty.finalizeOrder("Cash", "20"),

            // order with coupon code from coupon program
            // applied programs:
            //   - coupon program
            ProductScreen.addOrderline("Desk Organizer", "9"),
            PosLoyalty.hasRewardLine("on the cheapest product", "-4.59"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.orderTotalIs("45.90"),
            PosLoyalty.enterCode("invalid_code"),
            Notification.has("invalid_code"),
            PosLoyalty.enterCode("1234"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-15.30"),
            PosLoyalty.finalizeOrder("Cash", "50"),

            // Use coupon but eventually remove the reward
            // applied programs:
            //   - on cheapest product
            ProductScreen.addOrderline("Letter Tray", "4"),
            ProductScreen.addOrderline("Desk Organizer", "9"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-4.59"),
            PosLoyalty.orderTotalIs("62.43"),
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-15.30"),
            PosLoyalty.orderTotalIs("47.13"),
            PosLoyalty.removeRewardLine("Free Product"),
            PosLoyalty.orderTotalIs("62.43"),
            PosLoyalty.finalizeOrder("Cash", "90"),

            // specific product discount
            // applied programs:
            //   - on cheapest product
            //   - on specific products
            ProductScreen.addOrderline("Magnetic Board", "10"), // 1.98
            ProductScreen.addOrderline("Desk Organizer", "3"), // 5.1
            ProductScreen.addOrderline("Letter Tray", "4"), // 4.8 tax 10%
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-1.78"),
            PosLoyalty.orderTotalIs("54.44"),
            PosLoyalty.enterCode("promocode"),
            PosLoyalty.hasRewardLine("50% on specific products", "-16.66"), // 17.55 - 1.78*0.5
            PosLoyalty.orderTotalIs("37.78"),
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
            PosLoyalty.hasRewardLine("on the cheapest product", "-4.59"),
            ProductScreen.addOrderline("Letter Tray", "4"), // 4.8 tax 10%
            PosLoyalty.hasRewardLine("on the cheapest product", "-4.59"),
            PosLoyalty.enterCode("123456"),
            PosLoyalty.hasRewardLine("10% on your order", "-4.64"),
            PosLoyalty.hasRewardLine("10% on your order", "-2.11"),
            PosLoyalty.orderTotalIs("60.78"), //SUBTOTAL
            PosLoyalty.finalizeOrder("Cash", "70"),

            // Scanning coupon twice.
            // Also apply global discount on top of free product to check if the
            // calculated discount is correct.
            // Applied programs:
            //  - coupon program (free product)
            //  - global discount
            //  - on cheapest discount
            ProductScreen.addOrderline("Desk Organizer", "11"), // 5.1 per item
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-4.59"),
            PosLoyalty.orderTotalIs("51.51"),
            // add global discount and the discount will be replaced
            PosLoyalty.enterCode("345678"),
            PosLoyalty.hasRewardLine("10% on your order", "-5.15"),
            // add free product coupon (for qty=11, free=4)
            // the discount should change after having free products
            // it should go back to cheapest discount as it is higher
            PosLoyalty.enterCode("5678"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-20.40"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-4.59"),
            // set quantity to 18
            // free qty stays the same since the amount of points on the card only allows for 4 free products
            ProductScreen.clickNumpad("⌫", "8"),
            PosLoyalty.hasRewardLine("10% on your order", "-6.68"),
            PosLoyalty.hasRewardLine("Free Product - Desk Organizer", "-20.40"),
            // scan the code again and check notification
            PosLoyalty.enterCode("5678"),
            PosLoyalty.orderTotalIs("60.13"),
            PosLoyalty.finalizeOrder("Cash", "65"),

            // Specific products discount (with promocode) and free product (1357)
            // Applied programs:
            //   - discount on specific products
            //   - free product
            ProductScreen.addOrderline("Desk Organizer", "6"), // 5.1 per item
            PosLoyalty.hasRewardLine("on the cheapest product", "-4.59"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
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
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-2.87"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.63"),
            PosLoyalty.orderTotalIs("14.64"),
            PosLoyalty.removeRewardLine("90% on the cheapest product"),
            PosLoyalty.hasRewardLine("10% on your order", "-1.91"),
            PosLoyalty.orderTotalIs("17.23"),
            ProductScreen.clickControlButton("Reset Programs"),
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-2.87"),
            PosLoyalty.orderTotalIs("16.27"),
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
            ProductScreen.addOrderline("Test Product 1", "1.00", "100"),
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
            SelectionPopup.has("$ 1 per point on your order", { run: "click" }),
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

            ProductScreen.clickDisplayedProduct("Product A", true, "1.00", "15.00"),
            PosLoyalty.orderTotalIs("15.00"),

            ProductScreen.clickDisplayedProduct("Product B", true, "1.00", "50.00"),
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
            ProductScreen.selectedOrderlineHas("Product Test", "1.00"),
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
            ProductScreen.selectedOrderlineHas("Product A", "1.00", "20.00"),
            PosLoyalty.orderTotalIs("20.00"),

            ProductScreen.clickDisplayedProduct("Product B"),
            ProductScreen.selectedOrderlineHas("Product B", "1.00", "30.00"),
            PosLoyalty.orderTotalIs("50.00"),

            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.selectedOrderlineHas("Product A", "2.00", "40.00"),
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
            ProductScreen.selectedOrderlineHas("Free Product B", "6.00"),
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
            ProductScreen.selectedOrderlineHas("Desk Organizer", "1.00", "5.10"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            PosLoyalty.isRewardButtonHighlighted(true, true),
            PosLoyalty.claimReward("$ 2 on your order"),
            PosLoyalty.hasRewardLine("$ 2 on your order", "-2.00"),
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
            ProductScreen.selectedOrderlineHas("Test Product A", "1.00", "100.00"),
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
            ProductScreen.selectedOrderlineHas("Test Product A", "1.00", "100.00"),
            PosLoyalty.finalizeOrder("Cash", "100"),
        ].flat(),
});

registry.category("web_tour.tours").add("CustomerLoyaltyPointsDisplayed", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.clickDisplayedProduct("product_a"),
            ProductScreen.selectedOrderlineHas("product_a", "1.00", "100.00"),

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

registry.category("web_tour.tours").add("PosRewardProductScan", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("95412427100283"),
            ProductScreen.selectedOrderlineHas("product_a", "1.00", "1,150.00"),
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
            ProductScreen.selectedOrderlineHas("product_a", "1.00", "1,150.00"),
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
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
        ].flat(),
});
