odoo.define('l10n_eg_pos_edi_eta.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosETAPaymentScreen = PaymentScreen =>
        class extends PaymentScreen {
            async _isOrderValid(isForceValidate) {
                let res = await super._isOrderValid(isForceValidate);
                const etaErrors = await this.check_eta_errors();
                if (etaErrors) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Cannot submit this receipt to the ETA'),
                        body: etaErrors,
                    });
                    return false;
                }
                return res;
            }
            async check_eta_errors() {
                return await this.rpc({
                    model: 'pos.order',
                    method: 'l10n_eg_pos_eta_check_pos_configuration',
                    args: [[], this.currentOrder.export_as_JSON()]
                });
            }
        };

    Registries.Component.extend(PaymentScreen, PosETAPaymentScreen);

    return PaymentScreen;
});
