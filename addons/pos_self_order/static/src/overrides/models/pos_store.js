/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.company_has_self_ordering = loadedData["company_has_self_ordering"];
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.name.startsWith('Self-Order')) {
            this.trackingNumber = "S" + this.trackingNumber
        }
    },

    export_as_JSON() {
        var json = super.export_as_JSON();
        if (this.table_stand_number) {
            json.table_stand_number = this.table_stand_number;
        }
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.table_stand_number = json.table_stand_number;
    },

    defaultTableNeeded(options) {
        return (
            super.defaultTableNeeded(...arguments) &&
            !this.name.includes("Kiosk") &&
            !this.name.includes("Self-Order")
        );
    },

    updateSequenceNumber(json){
        if(!json.name.startsWith('Self-Order')) {
            super.updateSequenceNumber(json);
        }
    }
});
