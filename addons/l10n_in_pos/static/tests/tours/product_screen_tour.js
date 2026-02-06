import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";

registry.category("web_tour.tours").add("test_product_long_press_india", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.longPressProduct("Test Product"),
            Dialog.is(),
            {
                content: "Check that VAT label is present in the product details popup",
                trigger: ".section-financials .vat-label:contains('GST')",
            },
            Chrome.endTour(),
        ].flat(),
});
