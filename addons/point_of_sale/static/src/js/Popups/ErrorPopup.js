odoo.define('point_of_sale.ErrorPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // formerly ErrorPopupWidget
    class ErrorPopup extends AbstractAwaitablePopup {
        static template = 'ErrorPopup';
    }
    ErrorPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error',
        body: '',
    };

    addComponents(Chrome, [ErrorPopup]);

    Registry.add('ErrorPopup', ErrorPopup);

    return { ErrorPopup };
});
