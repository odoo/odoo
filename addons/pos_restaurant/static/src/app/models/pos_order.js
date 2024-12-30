import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

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
    get isBooked() {
        const res = super.isBooked;
        if (this.config.module_pos_restaurant) {
            return super.isBooked || !this.isDirectSale;
        }
        return res;
    },
    amountPerGuest(numCustomers = this.customer_count) {
        if (numCustomers === 0) {
            return 0;
        }
        return this.getTotalDue() / numCustomers;
    },
    setBooked(booked) {
        this.uiState.booked = booked;
    },
    getName() {
        if (this.config.module_pos_restaurant) {
            if (this.isDirectSale) {
                return _t("Direct Sale");
            }
            if (this.getTable()) {
                const table = this.getTable();
                const child_tables = this.models["restaurant.table"].filter((t) => {
                    if (t.floor_id.id === table.floor_id.id) {
                        return table.isParent(t);
                    }
                });
                let name = "T " + table.table_number.toString();
                for (const child_table of child_tables) {
                    name += ` & ${child_table.table_number}`;
                }
                return name;
            }
        }
        return super.getName(...arguments);
    },
    get isDirectSale() {
        return Boolean(
            this.config.module_pos_restaurant &&
                !this.table_id &&
                !this.floating_order_name &&
                this.state == "draft"
        );
    },
    get isFilledDirectSale() {
        return this.isDirectSale && !this.isEmpty();
    },
    setPartner(partner) {
        if (this.config.module_pos_restaurant && this.isDirectSale) {
            this.floating_order_name = partner.name;
        }
        return super.setPartner(...arguments);
    },
});
