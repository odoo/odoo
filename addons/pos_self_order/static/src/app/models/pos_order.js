/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState.lastChangesSent = {};
    },
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
                this.removeOrderline(line);
            }
        }

        for (const line of data.lines) {
            const lineFound = this.lines.find((l) => l.uuid === line.uuid);

            if (!lineFound && line.product_id) {
                this.models["pos.order.line"].create({ order_id: this, ...line });
            }
        }
    },
    get isAlreadySent() {
        return this.id && this.access_token && this.pos_reference ? true : false;
    },
    get isSavedOnServer() {
        return this.isAlreadySent && this.hasNotAllLinesSent().length === 0;
    },
    hasNotAllLinesSent() {
        return this.lines.filter((line) => {
            const lastSend = this.uiState.lastChangesSent[line.uuid];

            if (!lastSend) {
                return true;
            }

            return lastSend.qty !== line.qty || line.isChange(lastSend);
        });
    },
});
