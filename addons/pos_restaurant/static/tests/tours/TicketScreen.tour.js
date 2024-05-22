odoo.define('pos_restaurant.tour.TicketScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    // New Ticket button should not be in the ticket screen if no table is selected.
    Chrome.do.clickTicketButton();
    TicketScreen.check.noNewTicketButton();
    TicketScreen.do.clickDiscard();

    // Deleting the last order in the table brings back to floorscreen
    FloorScreen.do.clickTable('T4');
    ProductScreen.check.isShown();
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(2, '-0001');
    TicketScreen.do.deleteOrder('-0001');
    FloorScreen.check.isShown();

    // Create 2 items in a table. From floorscreen, delete 1 item. Then select the other item.
    // Correct order and screen should be displayed and the BackToFloorButton is shown.
    FloorScreen.do.clickTable('T2');
    ProductScreen.exec.addOrderline('Minute Maid', '1', '2');
    ProductScreen.check.totalAmountIs('2.0');
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Coca-Cola', '2', '2');
    ProductScreen.check.totalAmountIs('4.0');
    Chrome.do.backToFloor();
    FloorScreen.check.orderCountSyncedInTableIs('T2', '2');
    Chrome.do.clickTicketButton();
    TicketScreen.do.deleteOrder('-0003');
    Chrome.do.confirmPopup();
    TicketScreen.do.selectOrder('-0002');
    ProductScreen.check.totalAmountIs('2.0');
    Chrome.check.backToFloorTextIs('Main Floor', 'T2');
    Chrome.do.backToFloor();

    // Make sure that order is deleted properly.
    FloorScreen.do.clickTable('T5');
    ProductScreen.exec.addOrderline('Minute Maid', '1', '3');
    ProductScreen.check.totalAmountIs('3.0');
    Chrome.do.backToFloor();
    FloorScreen.check.orderCountSyncedInTableIs('T5', '1');
    Chrome.do.clickTicketButton();
    TicketScreen.do.deleteOrder('-0004');
    Chrome.do.confirmPopup();
    TicketScreen.do.clickDiscard();
    FloorScreen.check.isShown();
    FloorScreen.check.orderCountSyncedInTableIs('T5', '0');
    FloorScreen.do.clickTable('T5');
    ProductScreen.check.orderIsEmpty();

    Tour.register('PosResTicketScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
