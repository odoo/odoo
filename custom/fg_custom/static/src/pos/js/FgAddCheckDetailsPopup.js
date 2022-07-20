odoo.define('fg_custom.FgCheckDetailsPopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _t } = require('web.core');
    const { parse } = require('web.field_utils');

    class FgCheckDetailsPopup extends AbstractAwaitablePopup {
        setup() {
            this.state = owl.hooks.useState({
                x_check_number: '',
                x_issuing_bank: '',
                x_check_date: '',
                inputHasError: false,
            });
        }
        confirm() {
            if (this.state.x_check_number == '' || this.state.x_issuing_bank == '' || this.state.x_check_date == '') {
                this.errorMessage = this.env._t('All fields are required.');
                this.state.inputHasError = true;
                return;
            }
            return super.confirm();
        }

        getPayload() {
            return {
                x_check_number: this.state.x_check_number,
                x_issuing_bank: this.state.x_issuing_bank,
                x_check_date: this.state.x_check_date,
                inputHasError: this.state.inputHasError,
            };
        }
    }

    FgCheckDetailsPopup.template = 'fg_custom.FgCheckDetailsPopup';
     FgCheckDetailsPopup.defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Check Details'),
    };
    Registries.Component.add(FgCheckDetailsPopup);

    return FgCheckDetailsPopup;
});
