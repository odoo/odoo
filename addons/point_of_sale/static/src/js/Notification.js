/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";

const { onMounted } = owl;

export class Notification extends PosComponent {
    static template = "Notification";

    setup() {
        super.setup();
        useListener("click", this.closeNotification);

        onMounted(() => {
            setTimeout(() => {
                this.closeNotification();
            }, this.props.duration);
        });
    }
}
