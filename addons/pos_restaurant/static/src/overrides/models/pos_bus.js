/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            this.initTableOrderCount();
        }
        this.busService.subscribe("TABLE_ORDER_COUNT", (payload) => {
            if (this.pos.config.module_pos_restaurant) {
                this.ws_syncTableCount(payload);
            }
        });
    },

    async initTableOrderCount() {
        const result = await this.pos.data.call(
            "pos.config",
            "get_tables_order_count_and_printing_changes",
            [this.pos.config.id]
        );

        this.ws_syncTableCount(result);
    },

    // Sync the number of orders on each table with other PoS
    // using the same floorplan.
    async ws_syncTableCount(data) {
        const missingTable = data.find(
            (table) => !(table.id in this.pos.models["restaurant.table"].getAllBy("id"))
        );

        if (missingTable) {
            const response = await this.pos.data.searchRead("restaurant.floor", [
                ["pos_config_ids", "in", this.pos.config.id],
            ]);

            const table_ids = response.map((floor) => floor.raw.table_ids).flat();
            await this.pos.data.read("restaurant.table", table_ids);
        }

        for (const table of data) {
            this.pos.tableNotifications[table.id] = {
                order_count: table.orders,
                changes_count: table.changes,
                skip_changes: table.skip_changes,
            };
        }
    },
});
