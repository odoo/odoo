import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";

registry.category("web_tour.tours").add("GiftCardProgramCreateSetTour1", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramCreateSetTour2", {
    test: true,
    steps: () =>
        [
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramScanUseTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            // Pay the 5$ gift card.
            ProductScreen.clickDisplayedProduct("Gift Card"),
            TextInputPopup.inputText("043123456"),
            Dialog.confirm(),
            PosLoyalty.orderTotalIs("5.00"),
            PosLoyalty.finalizeOrder("Cash", "5"),
            // Partially use the gift card. (4$)
            ProductScreen.addOrderline("Desk Pad", "2", "2", "4.0"),
            PosLoyalty.enterCode("043123456"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
            // Use the remaining of the gift card. (5$ - 4$ = 1$)
            ProductScreen.addOrderline("Whiteboard Pen", "6", "6", "36.0"),
            PosLoyalty.enterCode("043123456"),
            PosLoyalty.orderTotalIs("35.00"),
            PosLoyalty.finalizeOrder("Cash", "35"),
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
            ProductScreen.clickDisplayedProduct("Gift Card"),
            TextInputPopup.inputText("044123456"),
            // pressing enter should confirm the text input popup
            { trigger: "textarea", run: "press Enter", in_modal: true },
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

registry.category("web_tour.tours").add("PosLoyaltyGiftCardNoPoints", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            TextInputPopup.inputText("044123456"),
            Dialog.confirm(),
            PosLoyalty.orderTotalIs("0.00"),
            ProductScreen.clickNumpad("Price"),
            ProductScreen.modeIsActive("Price"),
            ProductScreen.clickNumpad("5"),
            PosLoyalty.orderTotalIs("5.00"),
            PosLoyalty.finalizeOrder("Cash", "5"),
        ].flat(),
});
