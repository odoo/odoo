odoo.define('pos_mercury.PaymentTransactionPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { useState } = owl;

    class PaymentTransactionPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({ message: '', confirmButtonIsShown: false });
            this.props.transaction.then(data => {
                if (data.auto_close) {
                    setTimeout(() => {
                        this.confirm();
                    }, 2000)
                } else {
                    this.state.confirmButtonIsShown = true;
                }
                this.state.message = data.message;
            }).progress(data => {
                this.state.message = data.message;
            })
        }
    }
    PaymentTransactionPopup.template = 'PaymentTransactionPopup';
    PaymentTransactionPopup.defaultProps = {
        confirmText: _lt('Ok'),
        title: _lt('Online Payment'),
        body: '',
        cancelKey: false,
    };

    Registries.Component.add(PaymentTransactionPopup);

    return PaymentTransactionPopup;
});
