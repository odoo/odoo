/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/mobile/self_order_service";
import { browser } from "@web/core/browser/browser";

patch(SelfOrder.prototype, "pos_restaurant_self_order.SelfOrder", {
    async setup() {
        await this._super(...arguments);
        this.autoSelectTableFromIdentifier();
    },

    autoSelectTableFromIdentifier() {
        const url = new URL(browser.location.href);
        const tableIdentifier = url.searchParams.get("table_identifier");

        if (tableIdentifier) {
            const table = this.table_ids.find((table) => table.identifier === tableIdentifier);
            this.table = table;
        }
    },

    async sendDraftOrderToServer() {
        this.editedOrder.table_id = this.table.id;
        return await this._super(...arguments);
    },
});
