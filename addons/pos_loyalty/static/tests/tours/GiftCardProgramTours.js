/** @odoo-module **/

import * as PosLoyalty from "@pos_loyalty/../tests/tours/PosLoyaltyTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as TextInputPopup from "@point_of_sale/../tests/tours/helpers/TextInputPopupTourMethods";
import { registry } from "@web/core/registry";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";

//#region GiftCardProgramCreateSetTour1
registry.category("web_tour.tours").add("GiftCardProgramCreateSetTour1", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});
//#endregion

//#region GiftCardProgramCreateSetTour2
registry.category("web_tour.tours").add("GiftCardProgramCreateSetTour2", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.clickHomeCategory(),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});
//#endregion

//#region GiftCardProgramScanUseTour
registry.category("web_tour.tours").add("GiftCardProgramScanUseTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            // Pay the 5$ gift card.
            ProductScreen.clickDisplayedProduct("Gift Card"),
            TextInputPopup.isShown(),
            TextInputPopup.inputText("043123456"),
            TextInputPopup.clickConfirm(),
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
//#endregion

registry.category("web_tour.tours").add("GiftCardWithRefundtTour", {
    test: true,
    url: "/pos/web",
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Magnetic Board", "1"), // 1.98
            PosLoyalty.orderTotalIs("1.98"),
            PosLoyalty.finalizeOrder("Cash", "20"),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                withClass: ".selected",
                productName: "Magnetic Board",
            }),
            ProductScreen.pressNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "-1.00"),
            ProductScreen.addOrderline("Gift Card", "1"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1"),
            PosLoyalty.orderTotalIs("0.0"),
        ].flat(),
});
