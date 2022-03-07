odoo.define('point_of_sale.PaymentsDifferencePopup', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentsDifferencePopup extends PosComponent {
        confirm() {
            this.props.onConfirm();
        }
        discard() {
            this.props.onDiscard();
        }
    }

    PaymentsDifferencePopup.template = 'PaymentsDifferencePopup';
    Registries.Component.add(PaymentsDifferencePopup);

    return PaymentsDifferencePopup;

});
