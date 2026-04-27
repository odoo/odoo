/** @odoo-module **/

import BarcodePickingBatchModel from '@stock_barcode_picking_batch/models/barcode_picking_batch_model';
import MainComponent from '@stock_barcode/components/main';
import OptionLine from '@stock_barcode_picking_batch/components/option_line';

import { patch } from "@web/core/utils/patch";

patch(MainComponent.prototype, {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    confirm: function (ev) {
        ev.stopPropagation();
        this.env.model.confirmSelection();
    },

    async exit(ev) {
        if (this.state.view === 'barcodeLines' && this.env.model.canBeProcessed &&
            this.env.model.needPickings && !this.env.model.needPickingType && this.env.model.pickingTypes) {
            this.env.model.record.picking_type_id = false;
            return this.env.model.trigger('update');
        }
        return await super.exit(...arguments);
    },

    get isConfiguring() {
        return this.env.model.needPickingType || this.env.model.needPickings;
    },

    get displayActionButtons() {
        return super.displayActionButtons && !this.isConfiguring;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getModel() {
        const { resId, resModel, rpc, notification, orm, action } = this;
        if (this.resModel === 'stock.picking.batch') {
            return new BarcodePickingBatchModel(resModel, resId, { rpc, notification, orm, action });
        }
        return super._getModel(...arguments);
    },
});

MainComponent.components.OptionLine = OptionLine;
