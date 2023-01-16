odoo.define('pos_coupon.tour.pos_coupon3', function (require) {
    'use strict';

    // --- PoS Coupon Tour Basic Part 3 ---

    const { PosCoupon } = require('pos_coupon.tour.PosCouponTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickHomeCategory();

    ProductScreen.do.clickDisplayedProduct('Promo Product');
    PosCoupon.check.orderTotalIs('34.50');
    ProductScreen.do.clickDisplayedProduct('Product B');
    PosCoupon.check.hasRewardLine('100.0% discount on products', '25.00');
    ProductScreen.do.clickDisplayedProduct('Product A');
    PosCoupon.check.hasRewardLine('100.0% discount on products', '15.00');
    PosCoupon.check.orderTotalIs('34.50');
    ProductScreen.do.clickDisplayedProduct('Product A');
    PosCoupon.check.hasRewardLine('100.0% discount on products', '21.82');
    PosCoupon.check.hasRewardLine('100.0% discount on products', '18.18');
    PosCoupon.check.orderTotalIs('49.50');


    Tour.register('PosCouponTour3', { test: true, url: '/pos/web' }, getSteps());
});
