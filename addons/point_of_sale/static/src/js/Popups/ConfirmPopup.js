odoo.define('point_of_sale.ConfirmPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    // formerly ConfirmPopupWidget
    class ConfirmPopup extends AbstractAwaitablePopup {}
    ConfirmPopup.template = 'ConfirmPopup';
    ConfirmPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: _lt('Confirm ?'),
        body: '',
    };

    Registries.Component.add(ConfirmPopup);

    return ConfirmPopup;
});
