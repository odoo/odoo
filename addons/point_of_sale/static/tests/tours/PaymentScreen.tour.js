odoo.define('point_of_sale.tour.PaymentScreen', function (require) {
    'use strict';

    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { ErrorPopup } = require('point_of_sale.tour.ErrorPopupTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ReceiptScreen } = require('point_of_sale.tour.ReceiptScreenTourMethods');
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

    Chrome.do.clickTicketButton();
    TicketScreen.do.clickNewTicket();

    ProductScreen.exec.addOrderline('Product Test 1.2', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.00');
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('2');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('1.0');

    Tour.register('PaymentScreenRoundingHalfUp', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test 40', '1');
    ProductScreen.do.clickPartnerButton();
    ProductScreen.do.clickCustomer('Nicole Ford');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('40.00');
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.pressNumpad('3 8');
    PaymentScreen.check.remainingIs('2.0');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    PaymentScreen.do.clickInvoiceButton();
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();
    ReceiptScreen.do.clickNextOrder();

    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test 41', '1');
    ProductScreen.do.clickPartnerButton();
    ProductScreen.do.clickCustomer('Nicole Ford');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('41.00');
    PaymentScreen.do.clickPaymentMethod('Bank');
    PaymentScreen.do.pressNumpad('3 8');
    PaymentScreen.check.remainingIs('3.0');
    PaymentScreen.do.clickPaymentMethod('Cash');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('0.0');

    PaymentScreen.do.clickInvoiceButton();
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();

    Tour.register('PaymentScreenRoundingHalfUpCashAndBank', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Product Test', '1');
    ProductScreen.do.clickPayButton();

    PaymentScreen.check.totalIs('1.95');
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('5');

    PaymentScreen.check.remainingIs('0.0');
    PaymentScreen.check.changeIs('3.05');
    PaymentScreen.check.totalDueIs('1.95');

    Tour.register('PaymentScreenTotalDueWithOverPayment', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickHomeCategory();
    ProductScreen.exec.addOrderline('Magnetic Board', '1');
    ProductScreen.do.clickPayButton();

    // Check the popup error is shown when selecting another payment method
    PaymentScreen.check.totalIs('1.90');
    PaymentScreen.do.clickPaymentMethod('Cash');
    PaymentScreen.do.pressNumpad('1 .');
    PaymentScreen.check.selectedPaymentlineHas('Cash', '1.00');
    PaymentScreen.do.pressNumpad('2 4');
    PaymentScreen.check.selectedPaymentlineHas('Cash', '1.24');
    PaymentScreen.do.clickPaymentMethod('Bank');
    ErrorPopup.check.isShown();
    ErrorPopup.check.messageBodyContains(  // Verify the value displayed are as expected
        'The rounding precision is 0.10 so you should set 1.20 or 1.30 as payment amount instead of 1.24.'
    );

    Tour.register('CashRoundingPayment', { test: true, url: '/pos/ui' }, getSteps());

    startSteps();

    ProductScreen.exec.addOrderline('Letter Tray', '5');
    ProductScreen.check.selectedOrderlineHas('Letter Tray', '5.0');
    ProductScreen.do.clickPartnerButton();
    ProductScreen.do.clickCustomer('Nicole Ford');
    ProductScreen.do.clickPayButton();

    PaymentScreen.do.clickPaymentMethod('New Cash');
    PaymentScreen.do.pressNumpad('5 5');
    PaymentScreen.check.selectedPaymentlineHas('New Cash', '55');
    PaymentScreen.do.clickInvoiceButton();
    PaymentScreen.do.clickValidate();
    ReceiptScreen.check.receiptIsThere();

    Tour.register('MultipleCashPaymentMethod', { test: true, url: '/pos/ui' }, getSteps());
});
