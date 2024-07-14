/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BarcodePickingModel.prototype, {
    async validate() {
        if (this.currentState.lines.some(line => line.product_id.is_kits)) {
            await this.save();
            const move_ids = this.currentState.lines.reduce((mvIds, line) => line.product_id.is_kits ? [...mvIds, line.move_id] : mvIds, []);
            await this.orm.call(
                'stock.move',
                'action_explode',
                [move_ids],
            );
            this.trigger('refresh');
            return this.notification(_t("The lines with a kit have been replaced with their components. Please check the picking before the final validation."), {type: 'danger'});
        } else {
            return await super.validate();
        }
    },
});
