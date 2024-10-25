/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";


patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(loadedData);
        if (this.config.khmer_receipt) {
            this.currency_khr = (await this.orm.searchRead("res.currency", [["name", "=", "KHR"]], ["id"]))[0]
        }
    },

    getReceiptHeaderData() {
        const headerData = super.getReceiptHeaderData(...arguments);
        if (!this.config.khmer_receipt) return headerData;
        return {
            ...headerData,
            khmer_receipt: this.config.khmer_receipt
        };
    },
})
