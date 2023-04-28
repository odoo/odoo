odoo.define('pos_sale.tour', function (require) {
    'use strict';

    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ProductScreen } = require('pos_sale.tour.ProductScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickQuotationButton();
    ProductScreen.do.selectFirstOrder();
    ProductScreen.check.selectedOrderlineHas('Pizza Chicken', 9);
    ProductScreen.do.pressNumpad('Qty 2'); // Change the quantity of the product to 2
    ProductScreen.check.selectedOrderlineHas('Pizza Chicken', 2);
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    Chrome.do.clickTicketButton();

    Tour.register('PosSettleOrder', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickQuotationButton();
    ProductScreen.do.selectFirstOrder();
    ProductScreen.do.clickOrderline("Product A", "1");
    ProductScreen.check.selectedOrderlineHas('Product A', '1.00');
    ProductScreen.do.clickOrderline("Product B", "1");
    ProductScreen.do.pressNumpad('Qty 0');
    ProductScreen.check.selectedOrderlineHas('Product B', '0.00');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();

    Tour.register('PosSettleOrder2', { test: true, url: '/pos/ui' }, getSteps());
});
