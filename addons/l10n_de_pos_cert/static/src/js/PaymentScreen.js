odoo.define('l10n_de_pos_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosDePaymentScreen = PaymentScreen => class extends PaymentScreen {
        // Almost the same as in the basic module but we don't finalize if the api call has failed
        async validateOrder(isForceValidate) {
            if (await this._isOrderValid(isForceValidate)) {
                // remove pending payments before finalizing the validation
                for (let line of this.paymentLines) {
                    if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                }
                if (!this.currentOrder.isTransactionStarted()) {
                    await this.currentOrder.createTransaction().catch(async (error) => {
                        const message = {
                            'noInternet': this.env._t('Check the internet connection then try to validate the order again'),
                            'unknown': this.env._t('An unknown error has occurred ! Please, contact Odoo.')
                        }
                        this.trigger('fiskaly-error', { error, message })
                    });
                }
                if (this.currentOrder.isTransactionStarted()) {
                    await this.currentOrder.finishShortTransaction().then(async () => {
                        await this._finalizeValidation();
                    }).catch(async (error) => {
                        const message = {
                            'noInternet': this.env._t(
                                'The transaction has already been sent to Fiskaly. You still need to finish or cancel the transaction. ' +
                                'Check the internet connection then try to validate or cancel the order. ' +
                                'Do not delete your browsing, cookies and cache data in the meantime !'
                            ),
                            'unknown': this.env._t('An unknown error has occurred ! Please, cancel the order by deleting it and contact Odoo.')
                        }
                        this.trigger('fiskaly-error', { error, message })
                    });
                }
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
