import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as StockProductScreen from "@pos_stock/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_combo_price_unchanged_with_lot_tracked_product", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Test Combo"),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Test Combo"),
                ...ProductScreen.orderLineHas("Product A", "1.0"),
            ]),
            ProductScreen.totalAmountIs("8.05"),
            inLeftSide([
                ...StockProductScreen.clickLotIcon(),
                ...StockProductScreen.enterLotNumber("1", "lot"),
                ...ProductScreen.orderLineHas("Product A", "1.0"),
                {
                    trigger: ".info-list:contains('Lot 1')",
                },
            ]),
            ProductScreen.totalAmountIs("8.05"),
        ].flat(),
});
