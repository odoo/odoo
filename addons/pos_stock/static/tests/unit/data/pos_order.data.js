import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/../tests/unit/data/pos_order.data";

patch(PosOrder.prototype, {
    read_pos_data(orderIds, data, config_id) {
        const result = super.read_pos_data(orderIds, data, config_id);
        const lines = result["pos.order.line"] || [];
        const packLotLineIds = lines.flatMap((line) => line.pack_lot_ids || []);
        const packLotLines = this.env["pos.pack.operation.lot"].read(
            packLotLineIds,
            this.env["pos.pack.operation.lot"]._load_pos_data_fields(config_id),
            false
        );
        result["pos.pack.operation.lot"] = packLotLines;
        return result;
    },
    get_stock_reports_to_print() {
        return [
            {
                type: "ir.actions.report",
                report_name: "stock.report_return_document",
                report_type: "qweb-pdf",
                report_file: "return_slip",
                name: "Return slip",
            },
        ];
    },
});
