/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

const { onMounted } = owl;

class Notification extends PosComponent {
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
Notification.template = "Notification";

Registries.Component.add(Notification);

export default Notification;
