/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

// formerly ErrorPopupWidget
export class ErrorPopup extends AbstractAwaitablePopup {
    static template = "ErrorPopup";
    static defaultProps = {
        confirmText: _lt("Ok"),
        title: _lt("Error"),
        body: "",
        cancelKey: false,
    };

    setup() {
        super.setup();
        onMounted(this.onMounted);
        this.sound = useService("sound");
    }
    onMounted() {
        this.sound.play("error");
    }
}
