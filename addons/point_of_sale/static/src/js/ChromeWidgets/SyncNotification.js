/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class SyncNotification extends PosComponent {
    onClick() {
        this.env.pos.push_orders(null, { show_error: true });
    }
}
SyncNotification.template = "SyncNotification";

Registries.Component.add(SyncNotification);

export default SyncNotification;
