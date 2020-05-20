odoo.define('point_of_sale.tour.OrderManagementScreen', function (require) {
    'use strict';

    const { OrderManagementScreen } = require('point_of_sale.tour.OrderManagementScreenTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ClientListScreen } = require('point_of_sale.tour.ClientListScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { makeFullOrder } = require('point_of_sale.tour.CompositeTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    // Go by default to home category
    ProductScreen.do.clickHomeCategory();

    // make one order and check if it can be seen from the management screen.
    // order 0001
    makeFullOrder({ orderlist: [['Whiteboard Pen', '5', '6']], payment: ['Cash', '30'] });
    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.check.orderlistHas({ orderName: '-0001', total: '30' });

    OrderManagementScreen.do.clickBack();

    // make multiple orders and check them in the management screen.
    // order 0002
    makeFullOrder({
        orderlist: [
            ['Desk Pad', '1', '2'],
            ['Monitor Stand', '3', '4'],
            ['Whiteboard Pen', '5', '6'],
        ],
        payment: ['Bank', '44'],
    });
    // order 0003
    makeFullOrder({
        orderlist: [
            ['Desk Pad', '1', '2'],
            ['Whiteboard Pen', '5', '6'],
        ],
        customer: 'Colleen Diaz',
        payment: ['Cash', '50'],
    });
    // order 0004
    makeFullOrder({
        orderlist: [
            ['Monitor Stand', '3', '4'],
            ['Whiteboard Pen', '5', '6'],
        ],
        payment: ['Bank', '42'],
    });

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.check.orderlistHas({ orderName: '-0002', total: '44' });
    OrderManagementScreen.check.orderlistHas({
        orderName: '0003',
        total: '32',
        customer: 'Colleen Diaz',
    });
    OrderManagementScreen.check.orderlistHas({ orderName: '-0004', total: '42' });

    // click the currently active order
    OrderManagementScreen.do.clickOrder('-0005');
    ProductScreen.check.isShown();

    // Add 2 orders, they should appear in order management screen
    // order 0006
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Whiteboard Pen', '66', '6');

    // order 0007, should be at payment screen
    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Monitor Stand', '55', '5');
    ProductScreen.do.clickCustomerButton();
    ClientListScreen.exec.setClient('Azure Interior');
    ProductScreen.do.clickPayButton();

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.orderlistHas({ orderName: '-0006', total: '396' });
    OrderManagementScreen.check.orderlistHas({
        orderName: '-0007',
        total: '275',
        customer: 'Azure Interior',
    });

    // select a paid order, order row should be highlighted and should show order details
    OrderManagementScreen.do.clickOrder('-0004');
    OrderManagementScreen.check.highlightedOrderRowHas('-0004');
    OrderManagementScreen.check.orderDetailsHas({
        lines: [
            { product: 'Monitor Stand', quantity: '3' },
            { product: 'Whiteboard Pen', quantity: '5' },
        ],
        total: '42',
    });
    OrderManagementScreen.do.clickOrder('-0001');
    OrderManagementScreen.check.highlightedOrderRowHas('-0001');
    // 0004 should not be highlighted anymore
    OrderManagementScreen.check.orderRowIsNotHighlighted('-0004');
    OrderManagementScreen.check.orderDetailsHas({
        lines: [{ product: 'Whiteboard Pen', quantity: '5' }],
        total: '30',
    });

    // Select a paid order then invoice it. The selected order should remain selected
    // and will contain a new customer. After invoice, the current customer should be removed.
    // TODO: enable the following steps once the issue in invoicing is solved.
    // OrderManagementScreen.do.clickInvoiceButton();
    // Chrome.do.confirmPopup();
    // ClientListScreen.check.isShown();
    // ClientListScreen.exec.setClient('Jesse Brown');
    // OrderManagementScreen.check.highlightedOrderRowHas('Jesse Brown');

    // Check if order 0007 is selected, it should be at payment screen
    OrderManagementScreen.do.clickOrder('-0007');
    PaymentScreen.check.isShown();

    Chrome.do.clickOrderManagementButton();
    OrderManagementScreen.check.isShown();
    OrderManagementScreen.do.clickOrder('-0003');
    OrderManagementScreen.do.clickPrintReceiptButton();
    OrderManagementScreen.check.reprintReceiptIsShown();
    OrderManagementScreen.check.receiptChangeIs('18.0');
    OrderManagementScreen.check.receiptOrderDataContains('-0003');
    OrderManagementScreen.check.receiptAmountIs('32.0');
    OrderManagementScreen.do.closeReceipt();
    OrderManagementScreen.check.isNotHidden();

    Tour.register('OrderManagementScreenTour', { test: true, url: '/pos/ui' }, getSteps());
});
