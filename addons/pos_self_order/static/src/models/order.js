/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { Line } from "./line";

export class Order extends Reactive {
    constructor({
        id,
        access_token,
        pos_config_id,
        pos_reference,
        state,
        lines,
        date,
        amount_total,
        amount_tax,
        lastChangesSent,
    }) {
        super();
        this.setup(...arguments);
    }

    setup(order) {
        // server only data (recovered after first send to server)
        this.id = order.id || null;
        this.pos_config_id = order.pos_config_id;
        this.access_token = order.access_token || null;
        this.pos_reference = order.pos_reference || null;
        this.state = order.state || "draft";
        this.date = order.date || null;
        this.amount_total = order.amount_total || 0;
        this.amount_tax = order.amount_tax || 0;
        this.lines = order.lines || [];

        // data
        this.lastChangesSent = order.lastChangesSent || {};

        this.initLines();
    }

    get isAlreadySent() {
        return this.id && this.access_token && this.pos_reference ? true : false;
    }

    get totalQuantity() {
        return this.lines.reduce((acc, line) => (acc += line.qty), 0);
    }

    initLines() {
        this.lines = this.lines.map((line) => new Line(line));
    }

    computelastChangesSent() {
        for (const changeIdx in this.lastChangesSent) {
            const changeFound = this.lines.find((line) => line.uuid === changeIdx);
            if (!changeFound) {
                delete this.lastChangesSent[changeIdx];
            }
        }

        this.lastChangesSent = this.lines.reduce((acc, line) => {
            acc[line.uuid] = {
                qty: line.qty,
            };
            return acc;
        }, {});
    }

    isChange() {
        return this.lines.find((line) => {
            const lastSend = this.lastChangesSent[line.uuid];

            if (!lastSend) {
                return true;
            }

            return lastSend.qty !== line.qty;
        });
    }
}
