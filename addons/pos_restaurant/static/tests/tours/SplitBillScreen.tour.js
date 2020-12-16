odoo.define('pos_restaurant.tour.SplitBillScreen', function (require) {
    'use strict';

    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { ProductScreen } = require('pos_restaurant.tour.ProductScreenTourMethods');
    const { SplitBillScreen } = require('pos_restaurant.tour.SplitBillScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    FloorScreen.do.clickTable('T2');
    ProductScreen.exec.addOrderline('Water', '5', '2', '10.0');
    ProductScreen.exec.addOrderline('Minute Maid', '3', '2', '6.0');
    ProductScreen.exec.addOrderline('Coca-Cola', '1', '2', '2.0');
    ProductScreen.do.clickSplitBillButton();

    // Check if the screen contains all the orderlines
    SplitBillScreen.check.orderlineHas('Water', '5', '0');
    SplitBillScreen.check.orderlineHas('Minute Maid', '3', '0');
    SplitBillScreen.check.orderlineHas('Coca-Cola', '1', '0');

    // split 3 water and 1 coca-cola
    SplitBillScreen.do.clickOrderline('Water');
    SplitBillScreen.check.orderlineHas('Water', '5', '1');
    SplitBillScreen.do.clickOrderline('Water');
    SplitBillScreen.do.clickOrderline('Water');
    SplitBillScreen.check.orderlineHas('Water', '5', '3');
    SplitBillScreen.check.subtotalIs('6.0')
    SplitBillScreen.do.clickOrderline('Coca-Cola');
    SplitBillScreen.check.orderlineHas('Coca-Cola', '1', '1');
    SplitBillScreen.check.subtotalIs('8.0')

    // click pay to split, go back to check the lines
    SplitBillScreen.do.clickPay();
    PaymentScreen.do.clickBack();
    ProductScreen.do.clickOrderline('Water', '3.0')
    ProductScreen.do.clickOrderline('Coca-Cola', '1.0')

    // go back to the original order and see if the order is changed
    Chrome.do.clickTicketButton();
    TicketScreen.do.selectOrder('-0001');
    ProductScreen.do.clickOrderline('Water', '2.0')
    ProductScreen.do.clickOrderline('Minute Maid', '3.0')

    Tour.register('SplitBillScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
