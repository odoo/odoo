odoo.define('pos_gift_card.tour.pos_gift_card1', function (require) {
    'use strict';

    // A tour that add a product, add a coupon, add a global discount, and check the lines content.

    const { PosGiftCards } = require('pos_giftcard.tour.PosGiftCardsTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.clickHomeCategory();

    ProductScreen.exec.addOrderline('product1', '1.00', '10');
    PosGiftCards.do.useGiftCard('1234');
    ProductScreen.check.totalAmountIs('0.00');

    Tour.register('PosGiftCardTour', { test: true, url: '/pos/web' }, getSteps());
});
