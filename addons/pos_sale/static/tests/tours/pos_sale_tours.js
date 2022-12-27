odoo.define('pos_sale.tour', function (require) {
    'use strict';

    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ProductScreen } = require('pos_sale.tour.ProductScreenTourMethods');
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
});
