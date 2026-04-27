/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from "@web/core/utils/patch";

patch(BarcodePickingModel.prototype, {
    openQualityChecksMethod: 'check_quality',

    get displayOnDemandQualityCheckButton() {
        const { record } = this;
        return record && record.id && !["draft", "done", "cancel"].includes(record.state);
    }
});
