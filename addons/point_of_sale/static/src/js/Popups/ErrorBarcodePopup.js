odoo.define('point_of_sale.ErrorBarcodePopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    // formerly ErrorBarcodePopupWidget
    class ErrorBarcodePopup extends ErrorPopup {
        get translatedMessage() {
            return this.env._t(this.props.message);
        }
    }
    ErrorBarcodePopup.template = 'ErrorBarcodePopup';
    ErrorBarcodePopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: _lt('Error'),
        body: '',
        message:
            _lt('The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode.'),
    };

    Registries.Component.add(ErrorBarcodePopup);

    return ErrorBarcodePopup;
});
