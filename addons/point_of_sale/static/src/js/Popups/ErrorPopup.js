odoo.define('point_of_sale.ErrorPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    // formerly ErrorPopupWidget
    class ErrorPopup extends AbstractAwaitablePopup {
        mounted() {
            this.playSound('error');
        }
    }
    ErrorPopup.template = 'ErrorPopup';
    ErrorPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error',
        body: '',
    };

    Registries.Component.add(ErrorPopup);

    return ErrorPopup;
});
