import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";

function feeLineIsLast() {
    return inLeftSide({
        content: "the FBR service fee closes the order",
        trigger:
            '.order-container .orderline:last-child:has(.product-name:contains("FBR Service Fee"))',
    });
}

registry.category("web_tour.tours").add("l10n_pk_edi_pos_service_fee_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            inLeftSide(Order.doesNotHaveLine({ productName: "FBR Service Fee" })),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.orderLineHas("FBR Service Fee", "1.0", "1.0"),
            feeLineIsLast(),
            ProductScreen.addOrderline("Letter Tray", "1"),
            ProductScreen.orderLineHas("FBR Service Fee", "1.0", "1.0"),
            feeLineIsLast(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_pk_edi_pos_custom_service_fee_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.orderLineHas("Shop Service Charge", "1.0", "5.0"),
        ].flat(),
});
