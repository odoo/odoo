odoo.define('point_of_sale.tour.Chrome', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    // Order 1 is at Product Screen
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.order('Desk Pad', '1', '2');

    // Order 2 is at Payment Screen
    Chrome.do.newOrder();
    ProductScreen.exec.order('Monitor Stand', '3', '4');
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.isShown();

    // Order 3 is at Receipt Screen
    Chrome.do.newOrder();
    ProductScreen.exec.order('Whiteboard Pen', '5', '6');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();

    // Select order 1, should be at Product Screen
    Chrome.do.selectOrder('1');
    ProductScreen.check.productIsDisplayed('Desk Pad');
    ProductScreen.check.selectedOrderlineHas('Desk Pad', '1.0', '2.0');

    // Select order 2, should be at Payment Screen
    Chrome.do.selectOrder('2');
    PaymentScreen.check.emptyPaymentlines('12.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);

    // Select order 3, should be at Receipt Screen
    Chrome.do.selectOrder('3');
    ReceiptScreen.check.changeIs('0.0');

    // Pay order 1, with change
    Chrome.do.selectOrder('1');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('2 0');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.changeIs('18.0');

    // Select order 3, should still be at Receipt Screen
    // but change should be different.
    Chrome.do.selectOrder('3');
    ReceiptScreen.check.changeIs('0.0');

    // click next screen on order 3
    // then delete the new empty order
    ReceiptScreen.do.clickNextOrder();
    ProductScreen.check.orderIsEmpty();
    Chrome.do.deleteOrder();

    // Order 2 should be the current order
    // Deleting it should open a popup, confirm it.
    Chrome.do.deleteOrder();
    Chrome.do.confirmPopup();

    // Now left with order 1 in payment screen
    // go next screen
    ReceiptScreen.do.clickNextOrder();

    Tour.register('ChromeTour', { test: true, url: '/pos/web' }, getSteps());
});
