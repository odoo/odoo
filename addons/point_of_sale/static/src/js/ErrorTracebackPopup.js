odoo.define('point_of_sale.ErrorTracebackPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

    // formerly ErrorTracebackPopupWidget
    class ErrorTracebackPopup extends AbstractAwaitablePopup {}

    Chrome.addComponents([ErrorTracebackPopup]);

    return { ErrorTracebackPopup };
});
