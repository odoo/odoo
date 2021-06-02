odoo.define('pos_mercury.PaymentTransactionPopup', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const { _t } = require('web.core');

    class PaymentTransactionPopup extends owl.Component {
        constructor() {
            super(...arguments);
            this.state = useState({ message: '', confirmButtonIsShown: false });
            this.props.transaction.then(data => {
                if (data.auto_close) {
                    setTimeout(() => {
                        this.props.respondWith();
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
    PaymentTransactionPopup.template = 'pos_mercury.PaymentTransactionPopup';
    PaymentTransactionPopup.defaultProps = {
        confirmText: _t('Ok'),
        cancelText: _t('Cancel'),
        title: _t('Online Payment'),
        body: '',
    };

    return PaymentTransactionPopup;
});
