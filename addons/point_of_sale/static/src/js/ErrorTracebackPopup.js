odoo.define('point_of_sale.ErrorTracebackPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ErrorTracebackPopupWidget
    class ErrorTracebackPopup extends AbstractAwaitablePopup {}
    ErrorTracebackPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error with Traceback',
        body: '',
    };

    Chrome.addComponents([ErrorTracebackPopup]);

    return { ErrorTracebackPopup };
});
