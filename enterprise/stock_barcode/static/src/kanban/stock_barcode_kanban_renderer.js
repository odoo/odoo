/** @odoo-module **/

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { ManualBarcodeScanner } from "../components/manual_barcode";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { markup, onWillStart } from "@odoo/owl";

export class StockBarcodeKanbanRenderer extends KanbanRenderer {
    static template = "stock_barcode.KanbanRenderer";
    setup() {
        super.setup(...arguments);
        this.barcodeService = useService('barcode');
        this.dialogService = useService("dialog");
        this.resModel = this.props.list.model.config.resModel;
        this.displayTransferProtip = this.resModel === 'stock.picking';
        onWillStart(this.onWillStart);
    }

    openManualBarcodeDialog() {
        this.dialogService.add(ManualBarcodeScanner, {
            facingMode: "environment",
            onResult: (barcode) => {
                this.barcodeService.bus.trigger("barcode_scanned", { barcode });
            },
            onError: () => {},
        });
    }

    async onWillStart() {
        this.packageEnabled = await user.hasGroup('stock.group_tracking_lot');
        this.trackingEnabled = await user.hasGroup('stock.group_production_lot');
    }

    get transferTip() {
        if (this.trackingEnabled) {
            if (this.packageEnabled) {
                return _t(
                    "Scan a %(bold_start)s transfer%(bold_end)s, a %(bold_start)s product%(bold_end)s, a %(bold_start)s lot %(bold_end)s or a %(bold_start)s package %(bold_end)s to filter your records",
                    { bold_start: markup("<b>"), bold_end: markup("</b>") }
                );
            }
            return _t(
                "Scan a %(bold_start)s transfer%(bold_end)s, a %(bold_start)s product%(bold_end)s, or a %(bold_start)s lot %(bold_end)s to filter your records",
                { bold_start: markup("<b>"), bold_end: markup("</b>") }
            );
        }
        if (this.packageEnabled) {
            return _t(
                "Scan a %(bold_start)s transfer%(bold_end)s, a %(bold_start)s product%(bold_end)s, or a %(bold_start)s package %(bold_end)s to filter your records",
                { bold_start: markup("<b>"), bold_end: markup("</b>") }
            );
        }
        return _t(
            "Scan a %(bold_start)s transfer %(bold_end)s or a %(bold_start)s product %(bold_end)s to filter your records",
            { bold_start: markup("<b>"), bold_end: markup("</b>") }
        );
    }
}
