import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/../tests/unit/data/pos_order.data";

patch(PosOrder.prototype, {
    read_pos_data(orderIds, data, config_id) {
        const pos_data = super.read_pos_data(orderIds, data, config_id);
        const posPackOperationLot = [];
        const readOrder = this.read(orderIds, this._load_pos_data_fields(config_id), false);
        for (const order of readOrder) {
            const lines = this.env["pos.order.line"].read(
                order.lines,
                this.env["pos.order.line"]._load_pos_data_fields(config_id),
                false
            );
            const packLotLineIds = lines.flatMap((line) => line.pack_lot_ids);
            const packLotLines = this.env["pos.pack.operation.lot"].read(
                packLotLineIds,
                this.env["pos.pack.operation.lot"]._load_pos_data_fields(config_id),
                false
            );
            posPackOperationLot.push(...packLotLines);
        }
        return {
            ...pos_data,
            "pos.pack.operation.lot": posPackOperationLot,
        };
    },
});
