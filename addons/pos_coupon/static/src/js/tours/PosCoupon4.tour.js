odoo.define('pos_coupon.tour.pos_coupon4', function (require) {
    'use strict';

    // --- PoS Coupon Tour Basic Part 2 ---
    // Using the coupons generated from PosCouponTour1.

    const { PosCoupon } = require('pos_coupon.tour.PosCouponTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.clickHomeCategory();

    ProductScreen.exec.addOrderline('Test Product 1', '1');
    ProductScreen.exec.addOrderline('Test Product 2', '1');
    ProductScreen.do.clickPricelistButton();
    ProductScreen.do.selectPriceList('Public Pricelist');
    PosCoupon.do.enterCode('abcda');
    PosCoupon.check.orderTotalIs('0.00');
    ProductScreen.do.clickPricelistButton();
    ProductScreen.do.selectPriceList('Test multi-currency');
    PosCoupon.check.orderTotalIs('0.00');


    Tour.register('PosCouponTour4', { test: true, url: '/pos/web' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();

    ProductScreen.do.clickDisplayedProduct('Test Product 1');
    ProductScreen.do.clickDisplayedProduct('Test Product 2');
    ProductScreen.do.clickPricelistButton();
    ProductScreen.do.selectPriceList('Public Pricelist');
    PosCoupon.check.orderTotalIs('53.75');
    PosCoupon.do.enterCode('abcdb');
    PosCoupon.check.orderTotalIs('0.00');
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.dueIs('0.00');
    PaymentScreen.do.clickCustomerButton();
    PaymentScreen.do.clickCustomer('Colleen Diaz');
    PaymentScreen.do.clickValidateCustomer();
    PaymentScreen.check.dueIs('0.00');

    Tour.register('PosCouponTour4.1', { test: true, url: '/pos/web' }, getSteps());
});
