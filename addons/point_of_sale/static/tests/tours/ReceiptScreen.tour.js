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
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();
    ReceiptScreen.check.changeIs('0.00');
    ReceiptScreen.do.clickNextOrder();

    // pay more than total price
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.order('Desk Pad', '6', '5.0');
    ProductScreen.exec.order('Whiteboard Pen', '6', '6.1');
    ProductScreen.exec.order('Monitor Stand', '6', '1.3');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('8 0 0');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();
    ReceiptScreen.check.changeIs('725.6');
    ReceiptScreen.do.clickNextOrder();

    Tour.register('ReceiptScreenTour', { test: true, url: '/pos/web' }, getSteps());
});
