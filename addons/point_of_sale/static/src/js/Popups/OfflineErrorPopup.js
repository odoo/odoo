odoo.define('point_of_sale.OfflineErrorPopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    /**
     * This is a special kind of error popup as it introduces
     * an option to not show it again.
     */
    class OfflineErrorPopup extends ErrorPopup {
        dontShowAgain() {
            this.constructor.dontShow = true;
            this.cancel();
        }
    }
    OfflineErrorPopup.template = 'OfflineErrorPopup';
    OfflineErrorPopup.dontShow = false;
    OfflineErrorPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: _lt('Offline Error'),
        body: _lt('Either the server is inaccessible or browser is not connected online.'),
    };

    Registries.Component.add(OfflineErrorPopup);

    return OfflineErrorPopup;
});
