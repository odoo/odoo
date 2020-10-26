odoo.define('l10n_de_pos_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const Api = require('l10n_de_pos_cert.Api');

    const PosDePaymentScreen = PaymentScreen => class extends PaymentScreen {
        // Almost the same as in the basic module but we don't finalize if the api call has failed
        async validateOrder(isForceValidate) {
            if (await this._isOrderValid(isForceValidate)) {
                // remove pending payments before finalizing the validation
                for (let line of this.paymentLines) {
                    if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                }
                if (!this.currentOrder.isTransactionStarted()) {
                    await Api.createTransaction(this.currentOrder).catch(async (error) => {
                        if (error.status === 0) {
                            const title = this.env._t('No internet');
                            const body = this.env._t(
                                'Check the internet connection then try to validate the order again'
                            );
                            await this.showPopup('OfflineErrorPopup', { title, body });
                        } else {
                            const title = this.env._t('Unknown error');
                            const body = this.env._t(
                                'An unknown error has occurred ! Please, contact Odoo.'
                            );
                            await this.showPopup('ErrorPopup', { title, body });
                        }
                    });
                }
                if (this.currentOrder.isTransactionStarted()) {
                    await Api.finishShortTransaction(this.currentOrder).then(async () => {
                        await this._finalizeValidation();
                    }).catch(async (error) => {
                        if (error.status === 0) {
                            const title = this.env._t('No internet');
                            const body = this.env._t(
                                'The transaction has already been sent to Fiskaly. You still need to finish or cancel the transaction. ' +
                                'Check the internet connection then try to validate or cancel the order. ' +
                                'Do not delete your browsing, cookies and cache data in the meantime !'
                            );
                            await this.showPopup('OfflineErrorPopup', { title, body });
                        } else {
                            const title = this.env._t('Unknown error');
                            const body = this.env._t(
                                'An unknown error has occurred ! Please, cancel the order by deleting it and contact Odoo.'
                            );
                            await this.showPopup('ErrorPopup', { title, body });
                        }
                    });
                }
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
