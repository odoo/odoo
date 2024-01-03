/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SyncPopup } from "./sync_popup/sync_popup";

export class SyncNotification extends Component {
    static template = "point_of_sale.SyncNotification";
    static components = { SyncPopup };
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }
    get sync() {
        return {
            loading: this.pos.data.network.loading,
            offline: this.pos.data.network.offline,
            pending: this.pos.data.network.unsyncData.length,
        };
    }
    onClick() {
        if (this.pos.data.network.offline) {
            this.pos.data.network.warningTriggered = false;
        }

        if (this.pos.data.network.unsyncData.length > 0) {
            this.dialog.add(SyncPopup, {
                confirm: () => this.pos.data.syncData(),
            });
        }
    }
}
