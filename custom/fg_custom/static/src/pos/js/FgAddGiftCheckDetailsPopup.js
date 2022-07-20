odoo.define('fg_custom.FgGiftCheckDetailsPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgGiftCheckDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                x_gc_voucher_no: '',
                x_gc_voucher_name: '',
                x_gc_voucher_cust: '',
                inputHasError: false,
            });
        }
        confirm() {
            if (this.state.x_gc_voucher_no == '' || this.state.x_gc_voucher_name == '' || this.state.x_gc_voucher_cust == '') {
                this.errorMessage = this.env._t('All fields are required.');
                this.state.inputHasError = true;
                return;
            }
            return super.confirm();
        }

        getPayload() {
            return {
                x_gc_voucher_no: this.state.x_gc_voucher_no,
                x_gc_voucher_name: this.state.x_gc_voucher_name,
                x_gc_voucher_cust: this.state.x_gc_voucher_cust,
                inputHasError: this.state.inputHasError,
            };
        }
    }

    FgGiftCheckDetailsPopup.template = 'fg_custom.FgGiftCheckDetailsPopup';
     FgGiftCheckDetailsPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Gift Check Details'),
    };
    Registries.Component.add(FgGiftCheckDetailsPopup);

    return FgGiftCheckDetailsPopup;
});
