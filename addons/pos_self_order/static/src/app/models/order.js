/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";
import { Line } from "./line";
import { random5Chars } from "@point_of_sale/utils";

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
        take_away,
        tax_details,
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
        this.take_away = typeof order.take_away === "boolean" ? order.take_away : null;
        this.ticket_code = random5Chars(); // 5-digits alphanum code shown on the receipt
        this.tax_details = order.tax_details || [];

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

    get isSavedOnServer() {
        return this.isAlreadySent && this.hasNotAllLinesSent().length === 0;
    }

    get trackingNumber() {
        if (this.pos_reference) {
            const reference = this.pos_reference;
            const arrRef = reference.split(" ")[1].split("-");
            const sessionID = arrRef[0][4];
            const sequence = arrRef[2].substr(2, 2);
            const trackingNumber = sessionID + sequence;
            return trackingNumber;
        }
        return null;
    }

    initLines() {
        this.lines = this.lines.map((line) => new Line(line));
    }

    removeLine(lineUuid) {
        this.lines = this.lines.filter((line) => line.uuid !== lineUuid);
        for (const line of this.lines) {
            if (line.combo_parent_uuid === lineUuid) {
                this.removeLine(line.uuid);
            }
        }
    }

    updateLastChanges() {
        for (const changeIdx in this.lastChangesSent) {
            const changeFound = this.lines.find((line) => line.uuid === changeIdx);
            if (!changeFound) {
                delete this.lastChangesSent[changeIdx];
            }
        }

        this.lastChangesSent = this.lines.reduce((acc, line) => {
            acc[line.uuid] = {
                qty: line.qty,
                attribute_value_ids: [...line.attribute_value_ids],
                customer_note: line.customer_note,
            };
            return acc;
        }, {});
    }

    hasNotAllLinesSent() {
        return this.lines.filter((line) => {
            const lastSend = this.lastChangesSent[line.uuid];

            if (!lastSend) {
                return true;
            }

            return lastSend.qty !== line.qty || line.isChange(lastSend);
        });
    }

    updateDataFromServer(data) {
        for (const key in data) {
            if (key !== "lines") {
                this[key] = data[key];
            }
        }

        for (const line of this.lines) {
            const lineFound = data.lines.find((l) => l.uuid === line.uuid);

            if (lineFound) {
                line.updateDataFromServer(lineFound);
            } else if (line.id) {
                this.removeLine(line.uuid);
            }
        }

        for (const line of data.lines) {
            const lineFound = this.lines.find((l) => l.uuid === line.uuid);

            if (!lineFound && line.product_id) {
                this.lines.push(new Line(line));
            }
        }
    }
}
