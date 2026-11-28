import { patch } from "@web/core/utils/patch";
import { QtyAtDatePopover, qtyAtDateWidget } from "@sale_stock/widgets/qty_at_date_widget";

patch(QtyAtDatePopover.prototype, {
    openManufacturingForecast() {
        this.actionService.doAction("mrp.action_report_mrp_bom", {
            additionalContext: {
                active_id: this.props.record.data.manufacturing_bom_id.id,
                active_product_id: this.props.record.data.product_id.id,
                active_model: "product.product",
                mode: "forecast",
            },
        });
    },
});

patch(qtyAtDateWidget, {
    fieldDependencies: [
        ...qtyAtDateWidget.fieldDependencies,
        { name: "manufacturing_bom_id", type: "many2one", relation: "mrp.bom" },
    ],
});
