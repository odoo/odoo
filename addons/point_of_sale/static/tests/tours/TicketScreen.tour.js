odoo.define('point_of_sale.tour.TicketScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Desk Pad', '1', '2');
    ProductScreen.do.clickCustomerButton();
    ProductScreen.do.clickCustomer('Nicole Ford');
    ProductScreen.do.clickSetCustomer();
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(2, 'Nicole Ford');
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Desk Pad', '1', '3');
    ProductScreen.do.clickCustomerButton();
    ProductScreen.do.clickCustomer('Brandon Freeman');
    ProductScreen.do.clickSetCustomer();
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.isShown();
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(3, 'Brandon Freeman');
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Desk Pad', '1', '4');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(4, 'Receipt');
    TicketScreen.do.selectFilter('Receipt');
    TicketScreen.check.nthRowContains(2, 'Receipt');
    TicketScreen.do.selectFilter('Payment');
    TicketScreen.check.nthRowContains(2, 'Payment');
    TicketScreen.do.selectFilter('Ongoing');
    TicketScreen.check.nthRowContains(2, 'Ongoing');
    TicketScreen.do.selectFilter('All');
    TicketScreen.check.nthRowContains(4, 'Receipt');
    TicketScreen.do.search('Customer', 'Nicole');
    TicketScreen.check.nthRowContains(2, 'Nicole');
    TicketScreen.do.search('Customer', 'Brandon');
    TicketScreen.check.nthRowContains(2, 'Brandon');
    TicketScreen.do.search('Receipt Number', '-0003');
    TicketScreen.check.nthRowContains(2, 'Receipt');

    Tour.register('TicketScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
