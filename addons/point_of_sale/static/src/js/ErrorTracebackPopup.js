odoo.define('point_of_sale.ErrorTracebackPopup', function(require) {
    'use strict';

    const { JustOkayPopup } = require('point_of_sale.AbstractPopups');
    const { popupsRegistry } = require('point_of_sale.popupsRegistry');

    class ErrorTracebackPopup extends JustOkayPopup {}

    popupsRegistry.add(ErrorTracebackPopup);

    return { ErrorTracebackPopup };
});
