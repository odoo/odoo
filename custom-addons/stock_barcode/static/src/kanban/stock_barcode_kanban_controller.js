/** @odoo-module */

import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useBus, useService } from '@web/core/utils/hooks';
import { onMounted } from "@odoo/owl";

export class StockBarcodeKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.barcodeService = useService('barcode');
        useBus(this.barcodeService.bus, 'barcode_scanned', (ev) => this._onBarcodeScannedHandler(ev.detail.barcode));
        onMounted(() => {
            document.activeElement.blur();
        });
    }

    openRecord(record) {
        this.actionService.doAction('stock_barcode.stock_barcode_picking_client_action', {
            additionalContext: { active_id: record.resId },
        });
    }

    async createRecord() {
        const action = await this.model.orm.call(
            'stock.picking',
            'action_open_new_picking',
            [], { context: this.props.context }
        );
        if (action) {
            return this.actionService.doAction(action);
        }
        return super.createRecord(...arguments);
    }

    // --------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the user scans a barcode.
     *
     * @param {String} barcode
     */
    async _onBarcodeScannedHandler(barcode) {
        if (this.props.resModel != 'stock.picking') {
            return;
        }
        const kwargs = { barcode, context: this.props.context };
        const res = await this.model.orm.call(this.props.resModel, 'filter_on_barcode', [], kwargs);
        if (res.action) {
            this.actionService.doAction(res.action);
        } else if (res.warning) {
            const params = { title: res.warning.title, type: 'danger' };
            this.model.notification.add(res.warning.message, params);
        }
    }
}
