/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class NotificationSound extends PosComponent {
    setup() {
        super.setup();
        useListener("ended", () => (this.props.sound.src = null));
    }
}
NotificationSound.template = "NotificationSound";

Registries.Component.add(NotificationSound);

export default NotificationSound;
