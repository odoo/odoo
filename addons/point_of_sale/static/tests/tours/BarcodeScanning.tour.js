odoo.define('point_of_sale.tour.BarcodeScanning', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    startSteps();


    // Add a product with its barcode
    ProductScreen.do.scan_barcode("0123456789");
    ProductScreen.check.selectedOrderlineHas('Monitor Stand');
    ProductScreen.do.scan_barcode("0123456789");
    ProductScreen.check.selectedOrderlineHas('Monitor Stand', 2);

    // Test "Prices product" EAN-13 `23.....{NNNDD}` barcode pattern
    ProductScreen.do.scan_ean13_barcode("2305000000004");
    ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "0.00");
    ProductScreen.do.scan_ean13_barcode("2305000123454");
    ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "123.45");

    // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
    ProductScreen.do.scan_ean13_barcode("2100005000000");
    ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 0, "0.00");
    ProductScreen.do.scan_ean13_barcode("2100005080000");
    ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 8);


    Tour.register('BarcodeScanningTour', { test: true, url: '/pos/ui' }, getSteps());
});
