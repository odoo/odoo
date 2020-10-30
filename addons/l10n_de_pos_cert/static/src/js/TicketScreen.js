odoo.define('l10n_de_pos_cert.TicketScreen', function(require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');

    const PosDeTicketScreen = TicketScreen => class extends TicketScreen {
        // @Override
        async _canDeleteOrder(order) {
            if (order.isTransactionStarted()) {
                return order.cancelTransaction().catch(async (error) => {
                    const message = {
                        'noInternet': this.env._t(
                        'Check the internet connection then try to validate or cancel the order. ' +
                        'Do not delete your browsing, cookies and cache data in the meantime !'
                        ),
                        'unknown': this.env._t(
                            'An unknown error has occurred ! Try to validate this order or cancel it again. ' +
                            'Please contact Odoo for more information.'
                        )
                    };
                    this.trigger('fiskaly-error', { error, message });
                    // throw an error to stop the execution of deleteOrder(order), line 93 point_of_sale.TicketScreen
                    return Promise.reject();
                });
            }
        }
    };

    Registries.Component.extend(TicketScreen, PosDeTicketScreen);

    return PosDeTicketScreen;
});