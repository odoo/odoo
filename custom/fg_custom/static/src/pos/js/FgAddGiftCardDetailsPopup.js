odoo.define('fg_custom.FgGiftCardDetailsPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgGiftCardDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                x_gift_card_number: '',
                inputHasError: false,
            });
        }
        confirm() {
            if (this.state.x_gift_card_number == '') {
                this.errorMessage = this.env._t('All Gift Card Number is required.');
                this.state.inputHasError = true;
                return;
            }
            return super.confirm();
        }

        getPayload() {
            return {
                x_gift_card_number: this.state.x_gift_card_number,
                inputHasError: this.state.inputHasError,
            };
        }
    }
    FgGiftCardDetailsPopup.template = 'fg_custom.FgGiftCardDetailsPopup';
     FgGiftCardDetailsPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Gift Card Details'),
    };
    Registries.Component.add(FgGiftCardDetailsPopup);

    return FgGiftCardDetailsPopup;
});
