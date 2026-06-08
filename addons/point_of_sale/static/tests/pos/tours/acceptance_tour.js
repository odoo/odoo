import { registry } from "@web/core/registry";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { inLeftSide, waitForLoading } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";

registry.category("web_tour.tours").add("pos_basic_order_03_tax_position", {
    steps: () =>
        [
            waitForLoading(),
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1"),
            inLeftSide(...Order.hasTotal("5.28")),
            ProductScreen.clickFiscalPosition("FP-POS-2M", true),
            inLeftSide(...Order.hasTotal("5.52")),
            ProductScreen.closePos(),
        ].flat(),
});
