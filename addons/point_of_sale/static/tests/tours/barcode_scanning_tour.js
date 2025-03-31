import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/tours/utils/common";

registry.category("web_tour.tours").add("BarcodeScanningTour", {
    steps: () =>
        [
            // The following step is to make sure that the Chrome widget initialization ends
            // If we try to use the barcode parser before its initiation, we will have
            // some inconsistent JS errors:
            // TypeError: Cannot read properties of undefined (reading 'parse_barcode')
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add a product with its barcode
            scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Monitor Stand"),
            scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", 2),

            // Test "Prices product" EAN-13 `23.....{NNNDD}` barcode pattern
            scan_barcode("2305000000004"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", 1, "0.00"),
            scan_barcode("2305000123451"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", 1, "123.45"),

            // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
            scan_barcode("2100005000000"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 0, "0.00"),
            scan_barcode("2100005080002"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 8),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("BarcodeScanningProductPackagingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add the product with its barcode
            scan_barcode("12345601"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 1),
            scan_barcode("12345601"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 2),

            // Add the product packaging with its barcode
            scan_barcode("12345610"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 12),
            scan_barcode("12345610"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 22),
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
            ProductScreen.selectedOrderlineHas("Product 1"),
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1", 2),

            // Add the Product 2 with normal barcode
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2"),
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2", 2),

            // Add the Product 3 with normal barcode
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3"),
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3", 2),
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
            ProductScreen.customerIsSelected("John Doe"),
            Chrome.endTour(),
        ].flat(),
});
