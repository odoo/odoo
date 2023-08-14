odoo.define('point_of_sale.ErrorBarcodePopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');

    // formerly ErrorBarcodePopupWidget
    class ErrorBarcodePopup extends ErrorPopup {
        get translatedMessage() {
            return this.env._t(this.props.message);
        }
    }
    ErrorBarcodePopup.template = 'ErrorBarcodePopup';
    ErrorBarcodePopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error',
        body: '',
        message:
            'The Point of Sale could not find any product, client, employee or action associated with the scanned barcode.',
    };

    Registries.Component.add(ErrorBarcodePopup);

    return ErrorBarcodePopup;
});
