/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { _lt } from "@web/core/l10n/translation";

/**
 * This is a special kind of error popup as it introduces
 * an option to not show it again.
 */
export class OfflineErrorPopup extends ErrorPopup {
    static template = "OfflineErrorPopup";
    static dontShow = false;
    static defaultProps = {
        confirmText: _lt("Continue with limited functionalities"),
        title: _lt("You're offline"),
        body: _lt(
            "Meanwhile connection is back, Odoo Point of Sale will operate limited operations. Check your connection or continue with limited functionalities"
        ),
    };
    setup() {
        super.setup(...arguments);
        this.pos = usePos();

        if (!this.pos.globalState.showOfflineWarning) {
            this.cancel();
        } else {
            this.pos.globalState.set_synch("disconnected");
        }
    }

    confirm() {
        this.pos.globalState.showOfflineWarning = false;
        this.cancel();
    }
}
