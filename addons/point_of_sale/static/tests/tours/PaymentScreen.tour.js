odoo.define('point_of_sale.tour.PaymentScreen', function (require) {
    'use strict';

    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    startSteps();

    ProductScreen.exec.order('Letter Tray', '10');
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.emptyPaymentlines('52.8');

    // Pay with cash, created line should have zero amount
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('1 1');
    PaymentScreen.check.selectedPaymentlineHas('Cash', '11.00');
    PaymentScreen.check.remainingIs('41.8');
    PaymentScreen.check.changeIs('0.0');
    PaymentScreen.check.validateButtonIsHighlighted(false);
    // remove the selected paymentline with multiple backspace presses
    PaymentScreen.do.pressNumpad('Backspace Backspace Backspace');
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

    // toggle email button
    PaymentScreen.do.clickEmailButton();
    PaymentScreen.check.emailButtonIsHighligted(true);
    PaymentScreen.do.clickEmailButton();
    PaymentScreen.check.emailButtonIsHighligted(false);

    Tour.register('PaymentScreenTour', { test: true, url: '/pos/web' }, getSteps());
});
