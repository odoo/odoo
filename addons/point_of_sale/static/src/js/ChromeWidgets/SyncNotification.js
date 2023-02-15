/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class SyncNotification extends LegacyComponent {
    static template = "SyncNotification";

    onClick() {
        this.env.pos.push_orders(null, { show_error: true });
    }
}
