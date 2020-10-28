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
                        if (error.status === 0) {
                            const title = this.env._t('No internet');
                            const body = this.env._t(
                                'Check the internet connection then try to validate the order again'
                            );
                            await this.showPopup('OfflineErrorPopup', { title, body });
                        } else if (error.status === 401 && error.source === 'authenticate') {
                            await this.showForbiddenPopup();
                        } else if ((error.status === 400 && error.responseJSON.message.includes('tss_id')) ||
                            (error.status === 404 && error.responseJSON.code === 'E_TSS_NOT_FOUND')) {
                            await this.showBadRequestPopup('TSS ID');
                        } else if ((error.status === 400 && error.responseJSON.message.includes('client_id')) ||
                            (error.status === 400 && error.responseJSON.code === 'E_CLIENT_NOT_FOUND')) {
                            // the api is actually sending an 400 error for a "Not found" error
                            await this.showBadRequestPopup('Client ID');
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
                    await this.currentOrder.finishShortTransaction().then(async () => {
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
                        } else if (error.status === 401 && error.source === 'authenticate') {
                            await this.showForbiddenPopup();
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
        async showForbiddenPopup() {
            const title = this.env._t('Forbidden access to Fiskaly');
            const body = this.env._t(
                'It seems that your Fiskaly API key and/or secret are incorrect. Update them in your company settings.'
            );
            await this.showPopup('ErrorPopup', { title, body });
        }
        async showBadRequestPopup(data) {
            const title = this.env._t('Bad request');
            const body = this.env._t(`Your ${data} is incorrect. Update it in your PoS settings`);
            await this.showPopup('ErrorPopup', { title, body });
        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
