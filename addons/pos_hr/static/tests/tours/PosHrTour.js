odoo.define('point_of_sale.tour.PosHr', function (require) {
    'use strict';

    const { PosHr } = require('pos_hr.tour.PosHrTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { TicketScreen } = require('point_of_sale.tour.TicketScreenTourMethods');
    const { Chrome } = require('point_of_sale.tour.ChromeTourMethods');
    const { ErrorPopup } = require('point_of_sale.tour.ErrorPopupTourMethods');
    const { NumberPopup } = require('point_of_sale.tour.NumberPopupTourMethods');
    const { SelectionPopup } = require('point_of_sale.tour.SelectionPopupTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    startSteps();

    PosHr.check.loginScreenIsShown();
    PosHr.do.clickLoginButton();
    SelectionPopup.check.isShown();
    SelectionPopup.check.hasSelectionItem('Pos Employee1');
    SelectionPopup.check.hasSelectionItem('Pos Employee2');
    SelectionPopup.check.hasSelectionItem('Mitchell Admin');
    SelectionPopup.do.clickItem('Pos Employee1');
    NumberPopup.check.isShown();
    NumberPopup.do.pressNumpad('2 5');
    NumberPopup.check.inputShownIs('••');
    NumberPopup.do.pressNumpad('8 1');
    NumberPopup.check.inputShownIs('••••');
    NumberPopup.do.clickConfirm();
    ErrorPopup.check.isShown();
    ErrorPopup.do.clickConfirm();
    PosHr.do.clickLoginButton();
    SelectionPopup.do.clickItem('Pos Employee1');
    NumberPopup.check.isShown();
    NumberPopup.do.pressNumpad('2 5');
    NumberPopup.check.inputShownIs('••');
    NumberPopup.do.pressNumpad('8 0');
    NumberPopup.check.inputShownIs('••••');
    NumberPopup.do.clickConfirm();
    ProductScreen.check.isShown();
    ProductScreen.do.confirmOpeningPopup();
    PosHr.check.cashierNameIs('Pos Employee1');
    PosHr.do.clickCashierName();
    SelectionPopup.do.clickItem('Mitchell Admin');
    PosHr.check.cashierNameIs('Mitchell Admin');
    PosHr.do.clickLockButton();
    PosHr.do.clickLoginButton();
    SelectionPopup.do.clickItem('Pos Employee2');
    NumberPopup.do.pressNumpad('1 2');
    NumberPopup.check.inputShownIs('••');
    NumberPopup.do.pressNumpad('3 4');
    NumberPopup.check.inputShownIs('••••');
    NumberPopup.do.clickConfirm();
    ProductScreen.check.isShown();
    ProductScreen.do.clickHomeCategory();
    PosHr.check.cashInOutVisible(false);

    // Create orders and check if the ticket list has the right employee for each order
    // order for employee 2
    ProductScreen.exec.addOrderline('Desk Pad', '1', '2');
    ProductScreen.check.totalAmountIs('2.0')
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(2, 'Pos Employee2');

    // order for employee 1
    PosHr.do.clickLockButton();
    PosHr.exec.login('Pos Employee1', '2580');
    PosHr.check.cashInOutVisible();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Desk Pad', '1', '4');
    ProductScreen.check.totalAmountIs('4.0')
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(2, 'Pos Employee2');
    TicketScreen.check.nthRowContains(3, 'Pos Employee1');

    // order for admin
    PosHr.do.clickCashierName();
    SelectionPopup.do.clickItem('Mitchell Admin');
    PosHr.check.cashierNameIs('Mitchell Admin');
    PosHr.check.cashInOutVisible();
    TicketScreen.do.clickNewTicket();
    ProductScreen.exec.addOrderline('Desk Pad', '1', '8');
    ProductScreen.check.totalAmountIs('8.0')
    Chrome.do.clickTicketButton();
    TicketScreen.check.nthRowContains(4, 'Mitchell Admin');

    Tour.register('PosHrTour', { test: true, url: '/pos/ui' }, getSteps());
});
