odoo.define('point_of_sale.ErrorPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    // formerly ErrorPopupWidget
    class ErrorPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            owl.onMounted(this.onMounted);
        }
        onMounted() {
            this.playSound('error');
        }
    }
    ErrorPopup.template = 'ErrorPopup';
    ErrorPopup.defaultProps = {
        confirmText: _lt('Ok'),
        title: _lt('Error'),
        body: '',
        cancelKey: false,
    };

    Registries.Component.add(ErrorPopup);

    return ErrorPopup;
});
