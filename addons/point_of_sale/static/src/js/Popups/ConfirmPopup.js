odoo.define('point_of_sale.ConfirmPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { addComponents } = require('point_of_sale.PosComponent');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ConfirmPopupWidget
    class ConfirmPopup extends AbstractAwaitablePopup {
        static template = 'ConfirmPopup';
    }
    ConfirmPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Confirm ?',
        body: '',
    };

    addComponents(Chrome, [ConfirmPopup]);

    return { ConfirmPopup };
});
