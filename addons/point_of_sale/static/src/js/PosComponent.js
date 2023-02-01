/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

export class PosComponent extends LegacyComponent {
    static components = {};
    /**
     * Control the SyncNotification component.
     * @param {String} status 'connected' | 'connecting' | 'disconnected' | 'error'
     * @param {String} pending number of pending orders to sync
     */
    setSyncStatus(status, pending) {
        this.trigger("set-sync-status", { status, pending });
    }
}
