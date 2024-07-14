/** @odoo-module */

import { StockBarcodeKanbanRenderer } from '@stock_barcode/kanban/stock_barcode_kanban_renderer';
import { stockBarcodeKanbanView } from '@stock_barcode/kanban/stock_barcode_kanban_view';
import { StockBarcodeKanbanController } from '@stock_barcode/kanban/stock_barcode_kanban_controller';

export class StockBarcodeMRPKanbanRenderer extends StockBarcodeKanbanRenderer {
    setup(){
        super.setup(...arguments);
        this.display_protip = ['stock.picking', 'mrp.production'].includes(this.props.list.resModel);
    }
}

export class StockBarcodeMRPKanbanController extends StockBarcodeKanbanController {

    async createRecord() {
        if (this.props.resModel === 'mrp.production') {
            return this.actionService.doAction('stock_barcode_mrp.stock_barcode_mo_client_action');
        }
        return super.createRecord(...arguments);
    }

    openRecord(record) {
        if (this.props.resModel === 'mrp.production') {
            return this.actionService.doAction('stock_barcode_mrp.stock_barcode_mo_client_action', {
                additionalContext: { active_id: record.resId },
            });
        }
        return super.openRecord(...arguments);
    }

    async _onBarcodeScannedHandler(barcode) {
        if (this.props.resModel !== 'mrp.production') {
            return super._onBarcodeScannedHandler(...arguments);
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

StockBarcodeMRPKanbanRenderer.template = 'stock_barcode_mrp.KanbanRenderer';
stockBarcodeKanbanView.Renderer = StockBarcodeMRPKanbanRenderer;
stockBarcodeKanbanView.Controller = StockBarcodeMRPKanbanController;
