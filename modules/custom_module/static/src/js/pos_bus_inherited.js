/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    setup() {
        super.setup(...arguments);
        this.audio = new Audio('/custom_module/static/src/sounds/bell.wav');
        this.audio.preload = 'auto';
        if (this.pos.config.module_pos_restaurant) {
            this.initTableOrderCount();
        }
    },

    async initTableOrderCount() {
        const result = await this.orm.call(
            "pos.config",
            "get_tables_order_count_and_printing_changes",
            [this.pos.config.id]
        );

        this.ws_syncTableCount(result);
    },

    // @Override
    dispatch(message) {
        super.dispatch(...arguments);
        if (message.type === "SELF_ORDER_NOTIF" && this.pos.config.module_pos_restaurant) {
            this.playSound('/custom_module/static/src/sounds/bell.wav');
        }

        if (message.type === 'NEW_MOBILE_ORDER') {
            this.playSound('/custom_module/static/src/sounds/bell.wav');
        }

        if (message.type === "TABLE_ORDER_COUNT" && this.pos.config.module_pos_restaurant) {
            this.ws_syncTableCount(message.payload);
        }
    },

    playSound(soundFile) {
        fetch(soundFile, { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    const audio = new Audio(soundFile);
                    audio.muted = true;
                    audio.play().then(() => {
                        audio.muted = false;
                        audio.play().catch(error => {
                            console.log('Error playing sound after unmuting:', error);
                        });
                    }).catch(error => {
                        alert("Activez le son sur ce site pour entendre les notifications.");
                    });
                } else {
                    console.log(`Sound file not accessible: ${soundFile}`);
                }
            })
            .catch(error => {
                console.log('Error fetching sound file:', error);
            });
    },

    // Sync the number of orders on each table with other PoS
    // using the same floorplan.
    async ws_syncTableCount(data) {
        const missingTable = data.find((table) => !(table.id in this.pos.tables_by_id));

        if (missingTable) {
            const result = await this.orm.call("pos.session", "get_pos_ui_restaurant_floor", [
                [odoo.pos_session_id],
            ]);

            if (this.pos.config.module_pos_restaurant) {
                this.pos.floors = result;
                this.pos.loadRestaurantFloor();
            }
        }

        for (const floor of this.pos.floors) {
            floor.changes_count = 0;
        }
        for (const table of data) {
            const table_obj = this.pos.tables_by_id[table.id];
            if (table_obj) {
                table_obj.order_count = table.orders;
                table_obj.changes_count = table.changes;
                table_obj.skip_changes = table.skip_changes;
                table_obj.floor.changes_count += table.changes;
            }
        }
    },
});
