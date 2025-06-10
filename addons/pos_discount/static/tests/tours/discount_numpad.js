import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_discount_numpad", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "4", "25"),
            ProductScreen.clickControlButton("Discount"),
            NumberPopup.isShown("20 %"),
            NumberPopup.enterValue("10"),
            NumberPopup.clickType("fixed"),
            NumberPopup.hasTypeSelected("fixed"),
            NumberPopup.isShown("$ 10"),
            Dialog.confirm(),
            ProductScreen.checkTotalAmount("90"),
            ProductScreen.clickControlButton("Discount"),
            NumberPopup.isShown("20 %"),
            NumberPopup.enterValue("25"),
            NumberPopup.hasTypeSelected("percent"),
            NumberPopup.isShown("25 %"),
            Dialog.confirm(),
            ProductScreen.checkTotalAmount("75"),
            ProductScreen.cancelOrder(),
        ].flat(),
});
