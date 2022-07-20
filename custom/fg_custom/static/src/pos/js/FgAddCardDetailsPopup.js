odoo.define('fg_custom.FgCardDetailsPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgCardDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
//                x_card_number: '',
                x_card_name: '',
//                cardholder_name:'',
                x_approval_no: '',
//                x_batch_num: '',
                inputHasError: false,
            });
        }
        confirm() {
//            if (this.state.x_card_number == '' || this.state.x_card_name == '' || this.state.cardholder_name == '' || this.state.x_approval_no == '' ||  this.state.x_batch_num == '') {
            if (this.state.x_card_name == '' || this.state.x_approval_no == '' ) {
                this.errorMessage = this.env._t('All fields are required.');
                this.state.inputHasError = true;
                return;
            }
            return super.confirm();
        }

        getPayload() {
            return {
//                x_card_number: this.state.x_card_number,
                x_card_name: this.state.x_card_name,
//                cardholder_name: this.state.cardholder_name,
                x_approval_no: this.state.x_approval_no,
//                x_batch_num: this.state.x_batch_num,
                inputHasError: this.state.inputHasError,
            };
        }
    }
    FgCardDetailsPopup.template = 'fg_custom.FgCardDetailsPopup';
     FgCardDetailsPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Card Details'),
    };
    Registries.Component.add(FgCardDetailsPopup);

    return FgCardDetailsPopup;
});
