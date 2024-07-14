/** @odoo-module **/

import BarcodeMRPModel from '@stock_barcode_mrp/models/barcode_mrp_model';
import { patch } from "@web/core/utils/patch";

patch(BarcodeMRPModel.prototype, {
    openQualityChecksMethod: 'check_quality',

    get displayValidateButton() {
        return !(this.record && this.record.quality_check_todo) && super.displayValidateButton;
    }
});
