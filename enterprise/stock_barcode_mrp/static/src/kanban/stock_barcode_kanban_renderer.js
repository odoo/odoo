import { StockBarcodeKanbanRenderer } from '@stock_barcode/kanban/stock_barcode_kanban_renderer';
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";

patch(StockBarcodeKanbanRenderer.prototype, {
    get mrpKanbanTip() {
        return _t(
            "Scan an %(bold_start)s order %(bold_end)s or a %(bold_start)s product %(bold_end)s to filter your records",
            { bold_start: markup("<b>"), bold_end: markup("</b>") }
        );
    },
});
