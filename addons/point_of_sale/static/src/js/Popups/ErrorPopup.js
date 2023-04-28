/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/js/Popups/AbstractAwaitablePopup";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// formerly ErrorPopupWidget
export class ErrorPopup extends AbstractAwaitablePopup {
    static template = "ErrorPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: _lt("Error"),
        body: "",
        cancelKey: false,
    };
    static props = {
        ...AbstractAwaitablePopup.props,
        cancelText: { type: String, optional: true },
        confirmText: { type: String, optional: true },
        body: { type: String, optional: true },
        title: { type: String, optional: true },
    };

    setup() {
        super.setup();
        owl.onMounted(this.onMounted);
        this.sound = useService("sound");
    }
    onMounted() {
        this.sound.play("error");
    }
}
