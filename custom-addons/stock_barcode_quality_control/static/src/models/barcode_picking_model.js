/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from "@web/core/utils/patch";

patch(BarcodePickingModel.prototype, {
    openQualityChecksMethod: 'check_quality',

    get displayValidateButton() {
        return !(this.record && this.record.quality_check_todo) && super.displayValidateButton;
    }
});
