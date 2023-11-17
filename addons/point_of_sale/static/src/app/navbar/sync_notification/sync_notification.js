/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SyncNotification extends Component {
    static template = "point_of_sale.SyncNotification";

    setup() {
        this.pos = usePos();
    }
    get sync() {
        const pending =
            this.pos.db.get_orders().length + this.pos.db.get_ids_to_remove_from_server().length;

        return {
            loading: this.pos.data.network.loading,
            offline: this.pos.data.network.offline,
            pending: this.pos.data.network.unsyncData.length + pending,
        };
    }
    onClick() {
        if (this.pos.data.network.offline) {
            this.pos.data.network.warningTriggered = false;
        }
        this.pos.push_orders({ show_error: true });
    }
}
