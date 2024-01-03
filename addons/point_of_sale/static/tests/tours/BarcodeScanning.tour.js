/** @odoo-module */

import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("BarcodeScanningTour", {
    test: true,
    steps: () =>
        [
            // The following step is to make sure that the Chrome widget initialization ends
            // If we try to use the barcode parser before its initiation, we will have
            // some inconsistent JS errors:
            // TypeError: Cannot read properties of undefined (reading 'parse_barcode')
            Dialog.confirm("Open session"),

            // Add a product with its barcode
            ProductScreen.scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Monitor Stand"),
            ProductScreen.scan_barcode("0123456789"),
            ProductScreen.selectedOrderlineHas("Monitor Stand", 2),

            // Test "Prices product" EAN-13 `23.....{NNNDD}` barcode pattern
            ProductScreen.scan_ean13_barcode("2305000000004"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", 1, "0.00"),
            ProductScreen.scan_ean13_barcode("2305000123451"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", 1, "123.45"),

            // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
            ProductScreen.scan_ean13_barcode("2100005000000"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 0, "0.00"),
            ProductScreen.scan_ean13_barcode("2100005080002"),
            ProductScreen.selectedOrderlineHas("Wall Shelf Unit", 8),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("BarcodeScanningProductPackagingTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Add the product with its barcode
            ProductScreen.scan_barcode("12345601"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 1),
            ProductScreen.scan_barcode("12345601"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 2),

            // Add the product packaging with its barcode
            ProductScreen.scan_barcode("12345610"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 12),
            ProductScreen.scan_barcode("12345610"),
            ProductScreen.selectedOrderlineHas("Packaging Product", 22),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("GS1BarcodeScanningTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),

            // Add the Product 1 with GS1 barcode
            ProductScreen.scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1"),
            ProductScreen.scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1", 2),

            // Add the Product 2 with normal barcode
            ProductScreen.scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2"),
            ProductScreen.scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2", 2),

            // Add the Product 3 with normal barcode
            ProductScreen.scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3"),
            ProductScreen.scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3", 2),
            Chrome.endTour(),
        ].flat(),
});
