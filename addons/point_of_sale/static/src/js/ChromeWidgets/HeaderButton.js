odoo.define('point_of_sale.HeaderButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service')
    const { identifyError } = require('point_of_sale.utils');

    // Previously HeaderButtonWidget
    // This is the close session button
    class HeaderButton extends PosComponent {
        async onClick() {
            try {
                const info = await this.env.pos.getClosePosInfo();
                this.showPopup('ClosePosPopup', { info: info, keepBehind: true });
            } catch (e) {
                if (identifyError(e) instanceof ConnectionAbortedError||ConnectionLostError) {
                    this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Please check your internet connection and try again.'),
                    });
                } else {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Unknown Error'),
                        body: this.env._t('An unknown error prevents us from getting closing information.'),
                    });
                }
            }
        }
    }
    HeaderButton.template = 'HeaderButton';

    Registries.Component.add(HeaderButton);

    return HeaderButton;
});
