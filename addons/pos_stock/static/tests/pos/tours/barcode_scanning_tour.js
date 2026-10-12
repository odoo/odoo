import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("BarcodeScanningWeightedProductTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
            scan_barcode("2100005000000"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 0, "0.00"),
            scan_barcode("2100005080002"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 8),
            Chrome.endTour(),
        ].flat(),
});
