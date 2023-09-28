/** @odoo-module **/
import { Line } from "./line";
import { BaseOrder } from "@point_of_sale/app/base_models/base_order";

export class Order extends BaseOrder {
    setup(obj, order) {
        // server only data (recovered after first send to server)
        super.setup(obj, order);
        this.take_away = typeof order.take_away === "boolean" ? order.take_away : null;

        // data
        this.lastChangesSent = order.lastChangesSent || {};

        // this.initLines();
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

    initLines() {
        this.lines = this.lines.map((line) => new Line({ env: this.env }, line));
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
                selected_attributes: [...line.selected_attributes],
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
                this.lines.push(new Line({ env: this.env }, line));
            }
        }
    }
}
