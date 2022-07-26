odoo.define('point_of_sale.OrderImportPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    // formerly OrderImportPopupWidget
    class OrderImportPopup extends AbstractAwaitablePopup {
        get unpaidSkipped() {
            return (
                (this.props.report.unpaid_skipped_existing || 0) +
                (this.props.report.unpaid_skipped_session || 0)
            );
        }
        getPayload() {}
    }
    OrderImportPopup.template = 'OrderImportPopup';
    OrderImportPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelKey: false,
        body: '',
    };

    Registries.Component.add(OrderImportPopup);

    return OrderImportPopup;
});
