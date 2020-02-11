odoo.define('point_of_sale.ErrorPopup', function(require) {
    'use strict';

    const { JustOkayPopup } = require('point_of_sale.AbstractPopups');
    const { popupsRegistry } = require('point_of_sale.popupsRegistry');

    class ErrorPopup extends JustOkayPopup {}

    popupsRegistry.add(ErrorPopup);

    return { ErrorPopup };
});
