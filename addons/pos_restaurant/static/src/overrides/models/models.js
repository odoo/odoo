/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

// New orders are now associated with the current table, if any.
patch(Order.prototype, {
    setup(options) {
        super.setup(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.defaultTableNeeded(options)) {
                this.tableId = this.pos.table.id;
            }
            this.customerCount = this.customerCount || 1;
        }
    },
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            json.table_id = this.tableId;
            json.customer_count = this.customerCount;
        }

        return json;
    },
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            this.tableId = json.table_id;
            this.customerCount = json.customer_count;
        }
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
    defaultTableNeeded(options) {
        return !this.tableId && !options.json && this.pos.table;
    },
    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            set_tip_after_payment: this.pos.config.set_tip_after_payment,
        };
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.note = this.note || "";
    },
    //@override
    clone() {
        const orderline = super.clone(...arguments);
        orderline.note = this.note;
        return orderline;
    },
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.note = this.note;
        if (this.pos.config.iface_printers) {
            json.uuid = this.uuid;
        }
        return json;
    },
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
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
    toggleSkipChange() {
        if (this.hasChange || this.skipChange) {
            this.skipChange = !this.skipChange;
        }
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "has-change text-success border-start border-success border-4": this.hasChange,
            "skip-change text-primary border-start border-primary border-4": this.skipChange,
        };
    },
});

patch(Payment.prototype, {
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
