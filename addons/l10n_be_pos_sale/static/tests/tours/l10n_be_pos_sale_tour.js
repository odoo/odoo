odoo.define('l10n_be_pos_sale.tour', function (require) {
    'use strict';

    const { ErrorPopup } = require('point_of_sale.tour.ErrorPopupTourMethods');
    const { PaymentScreen } = require('point_of_sale.tour.PaymentScreenTourMethods');
    const { ProductScreen } = require('pos_sale.tour.ProductScreenTourMethods');
    const { getSteps, startSteps } = require('point_of_sale.tour.utils');
    const Tour = require('web_tour.tour');

    // signal to start generating steps
    // when finished, steps can be taken from getSteps
    startSteps();

    ProductScreen.do.confirmOpeningPopup();
    ProductScreen.do.clickQuotationButton();
    ProductScreen.do.selectFirstOrder();
    ProductScreen.do.clickPayButton();
    PaymentScreen.check.isInvoiceButtonChecked();
    PaymentScreen.do.clickInvoiceButton();
    PaymentScreen.check.isInvoiceButtonChecked();
    ErrorPopup.do.clickConfirm();

    Tour.register('PosSettleOrderIsInvoice', { test: true, url: '/pos/ui' }, getSteps());
});
