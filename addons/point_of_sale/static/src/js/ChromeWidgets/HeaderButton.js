/** @odoo-module */

<<<<<<< HEAD
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
||||||| parent of 1eb0b9d19e7 (temp)
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service')
    const { identifyError } = require('point_of_sale.utils');
=======
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');
>>>>>>> 1eb0b9d19e7 (temp)

<<<<<<< HEAD
// Previously HeaderButtonWidget
// This is the close session button
class HeaderButton extends PosComponent {
    async onClick() {
        const info = await this.env.pos.getClosePosInfo();
        this.showPopup("ClosePosPopup", { info: info, keepBehind: true });
||||||| parent of 1eb0b9d19e7 (temp)
    // Previously HeaderButtonWidget
    // This is the close session button
    class HeaderButton extends PosComponent {
        async onClick() {
            try {
                const info = await this.env.pos.getClosePosInfo();
                this.showPopup('ClosePosPopup', { info: info });
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
=======
    // Previously HeaderButtonWidget
    // This is the close session button
    class HeaderButton extends PosComponent {
        async onClick() {
            try {
                const info = await this.env.pos.getClosePosInfo();
                this.showPopup('ClosePosPopup', { info: info });
            } catch (e) {
                if (isConnectionError(e)) {
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
>>>>>>> 1eb0b9d19e7 (temp)
    }
}
HeaderButton.template = "HeaderButton";

Registries.Component.add(HeaderButton);

export default HeaderButton;
