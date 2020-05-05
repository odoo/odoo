odoo.define('pos_restaurant.tour.ControlButtons', function (require) {
    'use strict';

    const { TextAreaPopup } = require('pos_restaurant.tour.TextAreaPopupTourMethods');
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
    ProductScreen.exec.order('Water', '5.0', '2.0');
    ProductScreen.do.clickTransferButton();
    FloorScreen.do.clickTable('T4');
    ProductScreen.do.clickOrderline('Water', '5.0', '2.0');
    Chrome.do.backToFloor();
    FloorScreen.do.clickTable('T2');
    ProductScreen.check.orderIsEmpty();
    Chrome.do.backToFloor();
    FloorScreen.do.clickTable('T4');
    ProductScreen.do.clickOrderline('Water', '5.0', '2.0');

    // Test SplitBillButton
    ProductScreen.do.clickSplitBillButton();
    SplitBillScreen.do.clickBack();

    // Test OrderlineNoteButton
    ProductScreen.do.clickNoteButton();
    TextAreaPopup.check.isShown();
    TextAreaPopup.do.inputText('test note');
    TextAreaPopup.do.clickConfirm();
    ProductScreen.check.orderlineHasNote('Water', '5.0', 'test note');
    ProductScreen.exec.order('Water', '8', '1.1');
    ProductScreen.check.selectedOrderlineHas('Water', '8', '8.80');

    // Test PrintBillButton
    ProductScreen.do.clickPrintBillButton();
    BillScreen.check.isShown();
    BillScreen.do.clickBack();

    Tour.register('ControlButtonsTour', { test: true, url: '/pos/web' }, getSteps());
});
