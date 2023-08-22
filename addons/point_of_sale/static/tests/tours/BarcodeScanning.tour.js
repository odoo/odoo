/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("BarcodeScanningTour", {
        test: true,
        url: "/pos/ui",
        steps: () => {
            startSteps();

            // The following step is to make sure that the Chrome widget initialization ends
            // If we try to use the barcode parser before its initiation, we will have
            // some inconsistent JS errors:
            // TypeError: Cannot read properties of undefined (reading 'parse_barcode')
            ProductScreen.do.confirmOpeningPopup();

            // Add a product with its barcode
            ProductScreen.do.scan_barcode("0123456789");
            ProductScreen.check.selectedOrderlineHas('Monitor Stand');
            ProductScreen.do.scan_barcode("0123456789");
            ProductScreen.check.selectedOrderlineHas('Monitor Stand', 2);

            // Test "Prices product" EAN-13 `23.....{NNNDD}` barcode pattern
            ProductScreen.do.scan_ean13_barcode("2305000000004");
            ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "0.00");
            ProductScreen.do.scan_ean13_barcode("2305000123451");
            ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "123.45");

            // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
            ProductScreen.do.scan_ean13_barcode("2100005000000");
            ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 0, "0.00");
            ProductScreen.do.scan_ean13_barcode("2100005080002");
            ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 8);

            return getSteps();
        }
    });

registry
    .category("web_tour.tours")
    .add("BarcodeScanningProductPackagingTour", {
        test: true,
        url: "/pos/ui",
        steps: () => {
            startSteps();

            ProductScreen.do.confirmOpeningPopup();

            // Add the product with its barcode
            ProductScreen.do.scan_barcode('12345601');
            ProductScreen.check.selectedOrderlineHas('Packaging Product', 1);
            ProductScreen.do.scan_barcode('12345601');
            ProductScreen.check.selectedOrderlineHas('Packaging Product', 2);

            // Add the product packaging with its barcode
            ProductScreen.do.scan_barcode('12345610');
            ProductScreen.check.selectedOrderlineHas('Packaging Product', 12);
            ProductScreen.do.scan_barcode('12345610');
            ProductScreen.check.selectedOrderlineHas('Packaging Product', 22);

            return getSteps();
        }
    });
