odoo.define('point_of_sale.ErrorBarcodePopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ErrorBarcodePopupWidget
    class ErrorBarcodePopup extends AbstractAwaitablePopup {
        get translatedMessage() {
            return this.env._t(this.props.message);
        }
    }
    ErrorBarcodePopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error',
        body: '',
        message:
            'The Point of Sale could not find any product, client, employee or action associated with the scanned barcode.',
    };

    addComponents(Chrome, [ErrorBarcodePopup]);

    return { ErrorBarcodePopup };
});
