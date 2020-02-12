odoo.define('point_of_sale.ConfirmPopup', function(require) {
    'use strict';

    const { popupsRegistry } = require('point_of_sale.popupsRegistry');
    const { OkayCancelPopup } = require('point_of_sale.AbstractPopups');

    // formerly ConfirmPopupWidget
    class ConfirmPopup extends OkayCancelPopup {}

    popupsRegistry.add(ConfirmPopup);

    return { ConfirmPopup };
});
