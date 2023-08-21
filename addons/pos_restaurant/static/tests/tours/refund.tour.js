odoo.define('pos_restaurant.tour.Refund', function (require) {
    'use strict';

    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { ProductScreen } = require('pos_restaurant.tour.ProductScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    // Create first order and pay it
    FloorScreen.do.clickTable("T2");
    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickDisplayedProduct("Coca-Cola");
    ProductScreen.check.selectedOrderlineHas("Coca-Cola");
    ProductScreen.do.clickDisplayedProduct("Coca-Cola");
    ProductScreen.check.selectedOrderlineHas("Coca-Cola");
    ProductScreen.do.clickDisplayedProduct("Water");
    ProductScreen.check.selectedOrderlineHas("Water");
    ProductScreen.check.totalAmountIs("6.60");
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod("Cash");
    PaymentScreen.do.clickValidate();
    ReceiptScreen.do.clickNextOrder();

    // Go to another table and refund one of the product
    FloorScreen.do.clickTable("T4");
    ProductScreen.check.orderIsEmpty();
    ProductScreen.do.clickRefund();
    TicketScreen.do.selectOrder("-0001");
    TicketScreen.do.clickOrderline("Coca-Cola");
    TicketScreen.do.pressNumpad("2");
    TicketScreen.check.toRefundTextContains("To Refund: 2.00");
    TicketScreen.do.confirmRefund();
    ProductScreen.check.isShown();
    ProductScreen.check.selectedOrderlineHas("Coca-Cola");
    ProductScreen.check.totalAmountIs("-4.40");

    Tour.register('RefundStayCurrentTableTour', { test: true, url: '/pos/ui' }, getSteps());
});
