odoo.define('pos_restaurant.tour.OrderManagementScreen', function (require) {
    'use strict';

    // This tour tests the integration of OrderManagementScreen
    // to some pos_restaurant features.

    const { makeFullOrder } = require('point_of_sale.tour.CompositeTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const {
        OrderManagementScreen,
    } = require('point_of_sale.tour.OrderManagementScreenTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { ProductScreen } = require('pos_restaurant.tour.ProductScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    FloorScreen.do.clickTable('T2');

    // make one order and check if it can be seen from the management screen.
    makeFullOrder({ orderlist: [['Minute Maid', '5', '6']], payment: ['Cash', '30'] });
    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.check.orderlistHas({ orderName: '-0001', total: '30' });

    // go back to create multiple unpaid orders
    OrderManagementScreen.do.clickBack();

    // create 2 unpaid orders on T2 (orders 0002 and 0003)
    FloorScreen.do.clickTable('T2');
    ProductScreen.exec.addMultiOrderlines(
        ['Coca-Cola', '1', '2'],
        ['Water', '3', '4'],
        ['Minute Maid', '5', '6']
    );
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addMultiOrderlines(['Coca-Cola', '1', '2'], ['Minute Maid', '5', '6']);
    Chrome.do.backToFloor();

    // create 2 unpaid orders on T5 (orders 0004 and 0005)
    FloorScreen.do.clickTable('T5');
    ProductScreen.exec.addMultiOrderlines(
        ['Coca-Cola', '7', '8'],
        ['Water', '9', '10'],
        ['Minute Maid', '11', '12']
    );
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addMultiOrderlines(['Coca-Cola', '13', '14'], ['Minute Maid', '15', '16']);
    Chrome.do.backToFloor();

    // check that the unpaid orders are listed in the management screen
    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.check.orderlistHas({ orderName: '-0002', total: '44.0' });
    OrderManagementScreen.check.orderlistHas({ orderName: '-0003', total: '32.0' });
    OrderManagementScreen.check.orderlistHas({ orderName: '-0004', total: '278.0' });
    OrderManagementScreen.check.orderlistHas({ orderName: '-0005', total: '422.0' });

    // select order 0003 and check if it is really in T2
    OrderManagementScreen.do.clickOrder('-0003');
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('32');
    Chrome.check.backToFloorTextIs('Main Floor', 'T2');

    Chrome.do.clickOrderManagementButton();

    // select order 0005 and check it it is really in T5
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.do.clickOrder('-0005');
    ProductScreen.check.totalAmountIs('422');
    Chrome.check.backToFloorTextIs('Main Floor', 'T5');

    // go back to floor screen and start order management from there
    Chrome.do.backToFloor();
    FloorScreen.check.selectedFloorIs('Main Floor');
    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();

    // select order 0002 and check if it is really in T2
    OrderManagementScreen.do.clickOrder('-0002');
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('44');
    Chrome.check.backToFloorTextIs('Main Floor', 'T2');

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();

    // select order 0004 and check if it is really in T5
    OrderManagementScreen.do.clickOrder('-0004');
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('278');
    Chrome.check.backToFloorTextIs('Main Floor', 'T5');

    // transfer order 0004 to T2
    ProductScreen.do.clickTransferButton();
    FloorScreen.do.clickTable('T2');
    ProductScreen.check.isShown();

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();

    // select order 0004 and check if it is now in T2
    OrderManagementScreen.do.clickOrder('-0004', ['table', 'T2']);
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('278');
    Chrome.check.backToFloorTextIs('Main Floor', 'T2');

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();

    // finally, select order 0002
    OrderManagementScreen.do.clickOrder('-0002');
    ProductScreen.check.isShown();
    ProductScreen.check.totalAmountIs('44');
    Chrome.check.backToFloorTextIs('Main Floor', 'T2');

    Tour.register('PosResOrderManagementScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
