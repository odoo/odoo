odoo.define('point_of_sale.ConfirmPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ConfirmPopupWidget
    class ConfirmPopup extends AbstractAwaitablePopup {}
    ConfirmPopup.defaultProps = {
        title: 'Confirm ?',
        body: '',
    }

    Chrome.addComponents([ConfirmPopup]);

    return { ConfirmPopup };
});
