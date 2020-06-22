odoo.define('point_of_sale.tour.ReceiptScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    startSteps();

    // pay exact amount
    ProductScreen.exec.order('Letter Tray', '10');
    ProductScreen.check.selectedOrderlineHas('Letter Tray', '10');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.check.validateButtonIsHighlighted(true);
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();
    ReceiptScreen.check.changeIs('0.00');
    ReceiptScreen.do.clickNextOrder();

    // pay more than total price
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.order('Desk Pad', '6', '5', '30.0');
    ProductScreen.exec.order('Whiteboard Pen', '6', '6', '36.0');
    ProductScreen.exec.order('Monitor Stand', '6', '1', '6.0');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('7 0');
    PaymentScreen.check.remainingIs('2.0');
    PaymentScreen.do.pressNumpad('0');
    PaymentScreen.check.remainingIs('0.00');
    PaymentScreen.check.changeIs('628.0');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();
    ReceiptScreen.check.changeIs('628.0');
    ReceiptScreen.do.clickNextOrder();

    Tour.register('ReceiptScreenTour', { test: true, url: '/pos/web' }, getSteps());
});
