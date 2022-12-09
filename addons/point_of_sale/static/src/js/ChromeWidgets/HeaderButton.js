/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";
import { identifyError } from "@point_of_sale/js/utils";

// Previously HeaderButtonWidget
// This is the close session button
class HeaderButton extends PosComponent {
    async onClick() {
        try {
            const info = await this.env.pos.getClosePosInfo();
            this.showPopup("ClosePosPopup", { info: info, keepBehind: true });
        } catch (e) {
            if (identifyError(e) instanceof ConnectionAbortedError || ConnectionLostError) {
                this.showPopup("OfflineErrorPopup", {
                    title: this.env._t("Network Error"),
                    body: this.env._t("Please check your internet connection and try again."),
                });
            } else {
                this.showPopup("ErrorPopup", {
                    title: this.env._t("Unknown Error"),
                    body: this.env._t(
                        "An unknown error prevents us from getting closing information."
                    ),
                });
            }
        }
    }
}
HeaderButton.template = "HeaderButton";

Registries.Component.add(HeaderButton);

export default HeaderButton;
