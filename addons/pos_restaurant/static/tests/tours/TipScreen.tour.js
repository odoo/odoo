odoo.define('pos_restaurant.tour.TipScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { TipScreen } = require('pos_restaurant.tour.TipScreenTourMethods');
    const { NumberPopup } = require('point_of_sale.tour.NumberPopupTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    // Create order that is synced when draft.
    // order 1
    FloorScreen.do.clickTable('T2');
    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.exec.addOrderline('Minute Maid', '1', '2');
    ProductScreen.check.totalAmountIs('2.0');
    Chrome.do.backToFloor();
    FloorScreen.check.orderCountSyncedInTableIs('T2', '1');
    FloorScreen.do.clickTable('T2');
    ProductScreen.check.totalAmountIs('2.0');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    TipScreen.check.isShown();
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    // order 2
    ProductScreen.exec.addOrderline('Coca-Cola', '2', '2');
    ProductScreen.check.totalAmountIs('4.0');
    Chrome.do.backToFloor();
    FloorScreen.check.orderCountSyncedInTableIs('T2', '1');
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains('2', 'Tipping');
    TicketScreen.do.clickDiscard();

    // Create without syncing the draft.
    // order 3
    FloorScreen.do.clickTable('T5');
    ProductScreen.exec.addOrderline('Minute Maid', '3', '2');
    ProductScreen.check.totalAmountIs('6.0');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    TipScreen.check.isShown();
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    // order 4
    ProductScreen.exec.addOrderline('Coca-Cola', '4', '2');
    ProductScreen.check.totalAmountIs('8.0');
    Chrome.do.backToFloor();
    FloorScreen.check.orderCountSyncedInTableIs('T5', '1');
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains('3', 'Tipping');

    // Tip 20% on order1
    TicketScreen.do.selectOrder('-0001');
    TipScreen.check.isShown();
    TipScreen.check.totalAmountIs('2.0');
    TipScreen.check.percentAmountIs('15%', '0.30');
    TipScreen.check.percentAmountIs('20%', '0.40');
    TipScreen.check.percentAmountIs('25%', '0.50');
    TipScreen.do.clickPercentTip('20%');
    TipScreen.check.inputAmountIs('0.40')
    Chrome.do.backToFloor();
    FloorScreen.check.isShown();
    Chrome.do.clickTicketButton();

    // Tip 25% on order3
    TicketScreen.do.selectOrder('-0003');
    TipScreen.check.isShown();
    TipScreen.check.totalAmountIs('6.0');
    TipScreen.check.percentAmountIs('15%', '0.90');
    TipScreen.check.percentAmountIs('20%', '1.20');
    TipScreen.check.percentAmountIs('25%', '1.50');
    TipScreen.do.clickPercentTip('25%');
    TipScreen.check.inputAmountIs('1.50');
    Chrome.do.backToFloor();
    FloorScreen.check.isShown();
    Chrome.do.clickTicketButton();

    // finalize order 4 then tip custom amount
    TicketScreen.do.selectOrder('-0004');
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('8.0');
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.clickValidate();
    TipScreen.check.isShown();
    TipScreen.check.totalAmountIs('8.0');
    TipScreen.check.percentAmountIs('15%', '1.20');
    TipScreen.check.percentAmountIs('20%', '1.60');
    TipScreen.check.percentAmountIs('25%', '2.00');
    TipScreen.do.setCustomTip('1.00');
    TipScreen.check.inputAmountIs('1.00')
    Chrome.do.backToFloor();
    FloorScreen.check.isShown();

    // settle tips here
    Chrome.do.clickTicketButton();
    TicketScreen.do.selectFilter('Tipping');
    TicketScreen.check.tipContains('1.00');
    TicketScreen.do.settleTips();
    TicketScreen.do.selectFilter('All active orders');
    TicketScreen.check.nthRowContains(2, 'Ongoing');

    // tip order2 during payment
    // tip screen should not show after validating payment screen
    TicketScreen.do.selectOrder('-0002');
    ProductScreen.check.isShown();
    ProductScreen.do.clickPayButton();
    PaymentScreen.do.clickTipButton();
    NumberPopup.check.isShown();
    NumberPopup.do.pressNumpad('1');
    NumberPopup.check.inputShownIs('1');
    NumberPopup.do.clickConfirm();
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.isShown();

    Tour.register('PosResTipScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
