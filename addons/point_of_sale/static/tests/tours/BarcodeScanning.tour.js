/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

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
ProductScreen.do.scan_ean13_barcode("2301000000006");
ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "0.00");
ProductScreen.do.scan_ean13_barcode("2301000123453");
ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "123.45");

// Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
ProductScreen.do.scan_ean13_barcode("2100002000000");
ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 0, "0.00");
ProductScreen.do.scan_ean13_barcode("2100002080000");
ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 8);

Tour.register('BarcodeScanningTour', { test: true, url: '/pos/ui' }, getSteps());

startSteps();

ProductScreen.do.confirmOpeningPopup();

// Add the Product 1 with GS1 barcode
ProductScreen.do.scan_barcode("0108431673020125100000001");
ProductScreen.check.selectedOrderlineHas('Product 1');
ProductScreen.do.scan_barcode("0108431673020125100000001");
ProductScreen.check.selectedOrderlineHas('Product 1', 2);

// Add the Product 2 with normal barcode
ProductScreen.do.scan_barcode("08431673020126");
ProductScreen.check.selectedOrderlineHas('Product 2');
ProductScreen.do.scan_barcode("08431673020126");
ProductScreen.check.selectedOrderlineHas('Product 2', 2);

// Add the Product 3 with normal barcode
ProductScreen.do.scan_barcode("3760171283370");
ProductScreen.check.selectedOrderlineHas('Product 3');
ProductScreen.do.scan_barcode("3760171283370");
ProductScreen.check.selectedOrderlineHas('Product 3', 2);

Tour.register('GS1BarcodeScanningTour', { test: true, url: '/pos/ui' }, getSteps());
