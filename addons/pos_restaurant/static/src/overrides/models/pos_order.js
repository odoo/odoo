import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        if (this.config.module_pos_restaurant) {
            this.customer_count = this.customer_count || 1;
        }
    },
    getCustomerCount() {
        return this.customer_count;
    },
    setCustomerCount(count) {
        this.customer_count = Math.max(count, 0);
    },
    getTable() {
        return this.table_id;
    },
    amountPerGuest(numCustomers = this.customer_count) {
        if (numCustomers === 0) {
            return 0;
        }
        return this.getTotalDue() / numCustomers;
    },
    export_for_printing(baseUrl, headerData) {
        return {
            ...super.export_for_printing(...arguments),
            set_tip_after_payment: this.config.set_tip_after_payment,
            isRestaurant: this.config.module_pos_restaurant,
        };
    },
    setBooked(booked) {
        this.uiState.booked = booked;
    },
    getName() {
        if (this.config.module_pos_restaurant && this.getTable()) {
            const table = this.getTable();
            const child_tables = this.models["restaurant.table"].filter((t) => {
                if (t.floor_id.id === table.floor_id.id) {
                    return table.isParent(t);
                }
            });
            let name = table.table_number.toString();
            for (const child_table of child_tables) {
                name += ` & ${child_table.table_number}`;
            }
            return name;
        }
        return super.getName(...arguments);
    },
});
