/** @odoo-module **/

import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';
import { patch } from "@web/core/utils/patch";

patch(BarcodePickingBatchModel.prototype, {
    openQualityChecksMethod: 'action_open_quality_check_wizard',
});
