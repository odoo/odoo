/** @odoo-module */

import { Component } from "@odoo/owl";

export class SyncNotification extends Component {
    static template = "SyncNotification";
    static props = {};

    onClick() {
        this.env.pos.push_orders({ show_error: true });
    }
}
