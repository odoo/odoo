odoo.define('point_of_sale.tour.PaymentScreen', function (require) {
    'use strict';

    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.exec.addOrderline('Letter Tray', '10');
    ProductScreen.check.selectedOrderlineHas('Letter Tray', '10.0');
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.emptyPaymentlines('52.8');

    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('1 1');
    PaymentScreen.check.selectedPaymentlineHas('Cash', '11.00');
    PaymentScreen.check.remainingIs('41.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    // remove the selected paymentline with multiple backspace presses
    PaymentScreen.do.pressNumpad('Backspace Backspace');
    PaymentScreen.check.selectedPaymentlineHas('Cash', '0.00');
    PaymentScreen.do.pressNumpad('Backspace');
    PaymentScreen.check.emptyPaymentlines('52.8');

    // Pay with bank, the selected line should have full amount
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(true);
    // remove the line using the delete button
    PaymentScreen.do.clickPaymentlineDelButton('Bank', '52.8');

    // Use +10 and +50 to increment the amount of the paymentline
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('+10');
    PaymentScreen.check.remainingIs('42.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    PaymentScreen.do.pressNumpad('+50');
    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('7.2');
    PaymentScreen.check.validateButtonIsHighlighted(true);
    PaymentScreen.do.clickPaymentlineDelButton('Cash', '60.0');

    // Multiple paymentlines
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('1');
    PaymentScreen.check.remainingIs('51.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('5');
    PaymentScreen.check.remainingIs('46.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.pressNumpad('2 0');
    PaymentScreen.check.remainingIs('26.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(true);

    Tour.register('PaymentScreenTour', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Letter Tray', '1', '10');
    ProductScreen.do.clickPayButton();

    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.pressNumpad('1 0 0 0');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Tour.register('PaymentScreenTour2', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('2.00');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();

    ProductScreen.exec.addOrderline('Product Test', '-1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('-2.00');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Tour.register('PaymentScreenRoundingUp', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.95');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();

    ProductScreen.exec.addOrderline('Product Test', '-1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('-1.95');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Tour.register('PaymentScreenRoundingDown', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test 1.2', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.00');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();

    ProductScreen.exec.addOrderline('Product Test 1.25', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.5');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();

    ProductScreen.exec.addOrderline('Product Test 1.4', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.5');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    Tour.register('PaymentScreenRoundingHalfUp', { test: true, url: '/pos/ui' }, getSteps());

});
