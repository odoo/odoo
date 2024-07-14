/** @odoo-module */

import { onMounted } from "@odoo/owl";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";

export class IoTErrorPopup extends AbstractAwaitablePopup {
    static template = "pos_iot.IoTErrorPopup";
    static defaultProps = {
        confirmText: "Ok",
        title: "Error",
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
