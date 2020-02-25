odoo.define('point_of_sale.OrderImportPopup', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { AbstractAwaitablePopup } = require('point_of_sale.AbstractAwaitablePopup');

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
    OrderImportPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        body: '',
    };

    Chrome.addComponents([OrderImportPopup]);

    return { OrderImportPopup };
});
