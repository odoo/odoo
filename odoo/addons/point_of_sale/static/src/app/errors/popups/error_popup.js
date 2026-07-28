/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

export class ErrorPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.ErrorPopup";
    static defaultProps = {
        confirmText: _t("Ok"),
        title: _t("Error"),
        cancelKey: false,
        sound: true,
    };

    setup() {
        super.setup();
        onMounted(this.onMounted);
        this.sound = useService("sound");
    }
    onMounted() {
        if (this.sound) {
            this.sound.play("error");
        }
    }
}
