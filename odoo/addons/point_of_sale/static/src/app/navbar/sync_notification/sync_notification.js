/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SyncNotification extends Component {
    static template = "point_of_sale.SyncNotification";

    setup() {
        this.pos = usePos();
    }
    get sync() {
        return this.pos.synch;
    }
    onClick() {
        if (this.pos.synch.status !== "connected") {
            this.pos.showOfflineWarning = true;
        }
        this.pos.push_orders({ show_error: true });
    }
}
