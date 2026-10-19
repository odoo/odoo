// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { createDummyProductForEvents, updateSeats } from "../utils/event_util";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("UPDATE_AVAILABLE_SEATS", (data) => {
            updateSeats(this.models, data);
        });

        createDummyProductForEvents(this.models);
    },
});
