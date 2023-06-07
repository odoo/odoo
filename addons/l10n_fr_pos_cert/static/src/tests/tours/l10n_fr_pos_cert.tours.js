odoo.define('l10n_fr_pos_cert.tour.ProductScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('l10n_pos_fr_cert.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    ProductScreen.do.clickDisplayedProduct('Product A');
    ProductScreen.do.clickPricelistButton();
    ProductScreen.do.selectPriceList('special_pricelist');
    ProductScreen.check.OldUnitPriceIsShown('10.00');

    Tour.register('OldPriceProductTour', { test: true, url: '/pos/ui' }, getSteps());
});
