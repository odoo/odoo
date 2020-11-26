odoo.define('l10n_de_pos_cert.Chrome', function(require) {
    'use strict'

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');

    const PoSDeChrome = Chrome => class extends Chrome {
        // @Override
        constructor() {
            super(...arguments);
            useListener('fiskaly-error', this._fiskalyError);
        }
        async _fiskalyError(event) {
            let error = event.detail.error;
            if (error.status === 0) {
                const title = this.env._t('No internet');
                const body = event.detail.message.noInternet;
                await this.showPopup('OfflineErrorPopup', { title, body });
            } else if (error.status === 401 && error.source === 'authenticate') {
                await this._showUnauthorizedPopup();
            } else if ((error.status === 400 && error.responseJSON.message.includes('tss_id')) ||
                (error.status === 404 && error.responseJSON.code === 'E_TSS_NOT_FOUND')) {
                await this._showBadRequestPopup('TSS ID');
            } else if ((error.status === 400 && error.responseJSON.message.includes('client_id')) ||
                (error.status === 400 && error.responseJSON.code === 'E_CLIENT_NOT_FOUND')) {
                // the api is actually sending an 400 error for a "Not found" error
                await this._showBadRequestPopup('Client ID');
            } else {
                const title = this.env._t('Unknown error');
                const body = event.detail.message.unknown;
                await this.showPopup('ErrorPopup', { title, body });
            }
        }
        async _showUnauthorizedPopup() {
            const title = this.env._t('Unauthorized error to Fiskaly');
            const body = this.env._t(
                'It seems that your Fiskaly API key and/or secret are incorrect. Update them in your company settings.'
            );
            await this.showPopup('ErrorPopup', { title, body });
        }
        async _showBadRequestPopup(data) {
            const title = this.env._t('Bad request');
            const body = _.str.sprintf(this.env._t('Your %s is incorrect. Update it in your PoS settings'), data);
            await this.showPopup('ErrorPopup', { title, body });
        }
    };

    Registries.Component.extend(Chrome, PoSDeChrome);

    return Chrome;
});