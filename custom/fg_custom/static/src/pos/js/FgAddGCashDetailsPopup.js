odoo.define('fg_custom.FgGCashDetailsPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgGCashDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                x_gcash_refnum: '',
                x_gcash_customer: '',
                inputHasError: false,
            });
        }
        confirm() {
            if (this.state.x_gcash_refnum == '' || this.state.x_gcash_customer == '') {
                this.errorMessage = this.env._t('All GCash Details is required.');
                this.state.inputHasError = true;
                return;
            }
            return super.confirm();
        }

        getPayload() {
            return {
                x_gcash_refnum: this.state.x_gcash_refnum,
                x_gcash_customer: this.state.x_gcash_customer,
                inputHasError: this.state.inputHasError,
            };
        }
    }
    FgGCashDetailsPopup.template = 'fg_custom.FgGCashDetailsPopup';
     FgGCashDetailsPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('GCash Details'),
    };
    Registries.Component.add(FgGCashDetailsPopup);

    return FgGCashDetailsPopup;
});
