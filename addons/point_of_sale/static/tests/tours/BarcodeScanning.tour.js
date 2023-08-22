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
    ProductScreen.do.scan_ean13_barcode("2305000123451");
    ProductScreen.check.selectedOrderlineHas('Magnetic Board', 1, "123.45");

    // Test "Weighted product" EAN-13 `21.....{NNDDD}` barcode pattern
    ProductScreen.do.scan_ean13_barcode("2100005000000");
    ProductScreen.check.selectedOrderlineHas('Wall Shelf Unit', 0, "0.00");
    ProductScreen.do.scan_ean13_barcode("2100005080002");
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
});
