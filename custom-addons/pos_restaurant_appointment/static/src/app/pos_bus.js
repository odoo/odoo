/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    dispatch(message) {
        super.dispatch(...arguments);

        if (message.type === "TABLE_BOOKING") {
            this.ws_syncTableBooking(message.payload);
        }
    },

    ws_syncTableBooking(data) {
        const { command, table_event_pairs } = data;

        if (command === "ADDED") {
            for (const [tableId, event] of table_event_pairs) {
                const table = this.pos.tables_by_id[tableId];
                if (!table) {
                    continue;
                }
                table.appointment_ids[event.id] = event;
            }
        } else if (command === "REMOVED") {
            for (const [tableId, event] of table_event_pairs) {
                const table = this.pos.tables_by_id[tableId];
                if (!table) {
                    continue;
                }
                delete table.appointment_ids[event.id];
            }
        }
    },
});
