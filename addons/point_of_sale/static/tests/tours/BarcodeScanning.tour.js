/** @odoo-module */

import { ProductScreen } from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import { getSteps, startSteps } from "@point_of_sale/../tests/tours/helpers/utils";
import Tour from "web_tour.tour";

startSteps();

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
ProductScreen.do.scan_ean13_barcode("2100002000003");
ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 0, "0.00");
ProductScreen.do.scan_ean13_barcode("2100002080003");
ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 8);

Tour.register('BarcodeScanningTour', { test: true, url: '/pos/ui' }, getSteps());
