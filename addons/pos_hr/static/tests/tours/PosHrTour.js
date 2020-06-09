odoo.define('point_of_sale.tour.PosHr', function (require) {
    'use strict';

    const { PosHr } = require('pos_hr.tour.PosHrTourMethods');
    const { ProductScreen } = require('point_of_sale.tour.ProductScreenTourMethods');
    const { ErrorPopup } = require('point_of_sale.tour.ErrorPopupTourMethods');
    const { NumberPopup } = require('point_of_sale.tour.NumberPopupTourMethods');
    const { SelectionPopup } = require('point_of_sale.tour.SelectionPopupTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    startSteps();

    SelectionPopup.check.isShown();
    SelectionPopup.do.clickItem('Mitchell Admin');
    PosHr.check.cashierNameIs('Mitchell Admin');
    PosHr.do.clickCashierName();
    SelectionPopup.check.isShown();
    SelectionPopup.check.hasSelectionItem('Pos Employee1');
    SelectionPopup.check.hasSelectionItem('Pos Employee2');
    SelectionPopup.do.clickItem('Pos Employee1');
    NumberPopup.check.isShown();
    NumberPopup.do.pressNumpad('2 5 8 1');
    NumberPopup.check.inputShownIs('••••');
    NumberPopup.do.clickConfirm();
    ErrorPopup.check.isShown();
    ErrorPopup.do.clickConfirm();
    PosHr.do.clickCashierName();
    SelectionPopup.do.clickItem('Pos Employee1');
    NumberPopup.check.isShown();
    NumberPopup.do.pressNumpad('2 5 8 0');
    NumberPopup.check.inputShownIs('••••');
    NumberPopup.do.clickConfirm();
    ProductScreen.check.isShown();
    PosHr.check.cashierNameIs('Pos Employee1');
    PosHr.do.clickCashierName();
    SelectionPopup.do.clickItem('Mitchell Admin');
    PosHr.check.cashierNameIs('Mitchell Admin');
    PosHr.exec.login('Pos Employee2', '1234');
    ProductScreen.check.isShown();

    Tour.register('PosHrTour', { test: true, url: '/pos/web' }, getSteps());
});
