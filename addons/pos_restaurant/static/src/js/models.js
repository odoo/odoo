/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

// New orders are now associated with the current table, if any.
patch(Order.prototype, "pos_restaurant.Order", {
    setup(options) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (!this.tableId && !options.json && this.pos.table) {
                this.tableId = this.pos.table.id;
            }
            this.customerCount = this.customerCount || 1;
        }
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            json.table_id = this.tableId;
            json.customer_count = this.customerCount;
        }

        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            this.tableId = json.table_id;
            this.validation_date = moment.utc(json.creation_date).local().toDate();
            this.customerCount = json.customer_count;
        }
    },
    //@override
    export_for_printing() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.getTable()) {
                json.table = this.getTable().name;
            }
            json.customer_count = this.getCustomerCount();
        }
        return json;
    },
    getCustomerCount() {
        return this.customerCount;
    },
    setCustomerCount(count) {
        this.customerCount = Math.max(count, 0);
    },
    getTable() {
        if (this.pos.config.module_pos_restaurant) {
            return this.pos.tables_by_id[this.tableId];
        }
        return null;
    },
});

patch(Orderline.prototype, "pos_restaurant.Orderline", {
    setup() {
        this._super(...arguments);
        this.note = this.note || "";
    },
    //@override
    clone() {
        const orderline = this._super(...arguments);
        orderline.note = this.note;
        return orderline;
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        json.note = this.note;
        if (this.pos.config.iface_printers) {
            json.uuid = this.uuid;
        }
        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        this.note = json.note;
        if (this.pos.config.iface_printers) {
            this.uuid = json.uuid;
        }
    },
    get_line_diff_hash() {
        if (this.getNote()) {
            return this.id + "|" + this.getNote();
        } else {
            return "" + this.id;
        }
    },
});

patch(Payment.prototype, "pos_restaurant.Payment", {
    /**
     * Override this method to be able to show the 'Adjust Authorisation' button
     * on a validated payment_line and to show the tip screen which allow
     * tipping even after payment. By default, this returns true for all
     * non-cash payment.
     */
    canBeAdjusted() {
        if (this.payment_method.payment_terminal) {
            return this.payment_method.payment_terminal.canBeAdjusted(this.cid);
        }
        return !this.payment_method.is_cash_count;
    },
});
