import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";

registry.category("web_tour.tours").add("GiftCardProgramTour1", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramTour2", {
    test: true,
    steps: () =>
        [
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardWithRefundtTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.addOrderline("Magnetic Board", "1"), // 1.98
            PosLoyalty.orderTotalIs("1.98"),
            PosLoyalty.finalizeOrder("Cash", "20"),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                withClass: ".selected",
                productName: "Magnetic Board",
            }),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "-1.00"),
            ProductScreen.addOrderline("Gift Card", "1"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1"),
            PosLoyalty.orderTotalIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramPriceNoTaxTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            // Use gift card
            ProductScreen.addOrderline("Magnetic Board", "1", "1.98", "1.98"),
            PosLoyalty.enterCode("043123456"),
            Dialog.confirm(),
            ProductScreen.clickOrderline("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "-1.00"),
            PosLoyalty.orderTotalIs("0.98"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsGiftcard", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("044123456", 50),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            ProductScreen.addOrderline("product_a", "1"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.pointsAwardedAre("100"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyGiftCardTaxes", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("044123456", 50),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.checkTaxAmount("-6.52"),
        ].flat(),
});

registry.category("web_tour.tours").add("PhysicalGiftCardProgramSaleTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("test-card-0000", 125),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("test-card-0001", 100),
            PosLoyalty.clickPhysicalGiftCard("test-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "100"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("new-card-0001", 250),
            PosLoyalty.clickPhysicalGiftCard("new-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "250"),
            PosLoyalty.orderTotalIs("350"),
            PosLoyalty.finalizeOrder("Cash", "350"),
        ].flat(),
});
