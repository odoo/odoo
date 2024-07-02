import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

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
