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
    ProductScreen.check.totalAmountIs('94.50');

    Tour.register('PosCouponTour5', { test: true, url: '/pos/web' }, getSteps());
});
