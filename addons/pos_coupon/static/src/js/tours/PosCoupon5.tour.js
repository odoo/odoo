odoo.define('pos_coupon.tour.pos_coupon5', function (require) {
    'use strict';

    // A tour that add a product, add a coupon, add a global discount, and check the lines content.

    const { PosCoupon } = require('pos_coupon.tour.PosCouponTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.clickHomeCategory();

    ProductScreen.exec.addOrderline('Test Product 1', '1.00', '100');
    PosCoupon.do.clickDiscountButton();
    PosCoupon.do.clickConfirmButton();
    ProductScreen.check.totalAmountIs('93.15');

    Tour.register('PosCouponTour5', { test: true, url: '/pos/web' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.do.confirmOpeningPopup();

    ProductScreen.exec.addOrderline('Test Product 1', '1.00', '100');
    ProductScreen.do.clickCustomerButton();
    ProductScreen.do.clickCustomer('Test Partner');
    ProductScreen.do.clickSetCustomer();
    PosCoupon.do.clickRewardButton();
    ProductScreen.check.totalAmountIs('93.50');

    Tour.register('PosCouponTour5.1', { test: true, url: '/pos/web' }, getSteps());


    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.do.confirmOpeningPopup();

    ProductScreen.do.clickDisplayedProduct('Product B');
    ProductScreen.do.clickDisplayedProduct('Product A');
    ProductScreen.check.totalAmountIs('50.00');

    Tour.register('PosCouponTour5.2', { test: true, url: '/pos/web' }, getSteps());
});
