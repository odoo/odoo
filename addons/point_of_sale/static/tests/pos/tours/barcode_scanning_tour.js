import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("BarcodeScanningTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add a product with its barcode
            scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Quality Item"),
            scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Quality Item", 2),

            // Test "Prices product" EAN-13 `23.....{NNNDD}` barcode pattern
            scan_barcode("2305000000004"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 1, "0.00"),
            scan_barcode("2305000123451"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 1, "123.45"),

            // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
            scan_barcode("2100005000000"),
            ProductScreen.selectedOrderlineHas("Quality Article", 0, "0.00"),
            scan_barcode("2100005080002"),
            ProductScreen.selectedOrderlineHas("Quality Article", 8),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("BarcodeScanningProductPackagingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add the product with its barcode
            scan_barcode("19971997"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 1),
            scan_barcode("19971997"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 2),

            // Add the product packaging with its barcode
            scan_barcode("19981998"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 12),
            scan_barcode("19981998"),
            ProductScreen.selectedOrderlineHas("Quality Thing", 22),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("GS1BarcodeScanningTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add the Product 1 with GS1 barcode
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Awesome Article"),
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Awesome Article", 2),

            // Add the Product 2 with normal barcode
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Awesome Item"),
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Awesome Item", 2),

            // Add the Product 3 with normal barcode
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Awesome Thing"),
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Awesome Thing", 2),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("BarcodeScanPartnerTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // scan the customer barcode
            scan_barcode("0421234567890"),
            ProductScreen.customerIsSelected("Partner One"),
            Chrome.endTour(),
        ].flat(),
});
