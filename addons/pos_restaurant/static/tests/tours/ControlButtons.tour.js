odoo.define('pos_restaurant.tour.ControlButtons', function (require) {
    'use strict';

    const { TextAreaPopup } = require('point_of_sale.tour.TextAreaPopupTourMethods');
    const { NumberPopup } = require('point_of_sale.tour.NumberPopupTourMethods');
    const { Chrome } = require('pos_restaurant.tour.ChromeTourMethods');
    const { FloorScreen } = require('pos_restaurant.tour.FloorScreenTourMethods');
    const { ProductScreen } = require('pos_restaurant.tour.ProductScreenTourMethods');
    const { SplitBillScreen } = require('pos_restaurant.tour.SplitBillScreenTourMethods');
    const { BillScreen } = require('pos_restaurant.tour.BillScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    var Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    // Test TransferOrderButton
    FloorScreen.do.clickTable('T2');
    ProductScreen.exec.addOrderline('Water', '5', '2', '10.0');
    ProductScreen.do.clickTransferButton();
    FloorScreen.do.clickTable('T4');
    ProductScreen.do.clickOrderline('Water', '5', '2');
    Chrome.do.backToFloor();
    FloorScreen.do.clickTable('T2');
    ProductScreen.check.orderIsEmpty();
    Chrome.do.backToFloor();
    FloorScreen.do.clickTable('T4');
    ProductScreen.do.clickOrderline('Water', '5', '2');

    // Test SplitBillButton
    ProductScreen.do.clickSplitBillButton();
    SplitBillScreen.do.clickBack();

    // Test OrderlineNoteButton
    ProductScreen.do.clickNoteButton();
    TextAreaPopup.check.isShown();
    TextAreaPopup.do.inputText('test note');
    TextAreaPopup.do.clickConfirm();
    ProductScreen.check.orderlineHasNote('Water', '5', 'test note');
    ProductScreen.exec.addOrderline('Water', '8', '1', '8.0');

    // Test PrintBillButton
    ProductScreen.do.clickPrintBillButton();
    BillScreen.check.isShown();
    BillScreen.do.clickOk();

    // Test GuestButton
    ProductScreen.do.clickGuestButton();
    NumberPopup.do.pressNumpad('1 5');
    NumberPopup.check.inputShownIs('15');
    NumberPopup.do.clickConfirm();
    ProductScreen.check.guestNumberIs('15')

    ProductScreen.do.clickGuestButton();
    NumberPopup.do.pressNumpad('5');
    NumberPopup.check.inputShownIs('5');
    NumberPopup.do.clickConfirm();
    ProductScreen.check.guestNumberIs('5')

    Tour.register('ControlButtonsTour', { test: true, url: '/pos/ui' }, getSteps());
});
