import { useState } from "@odoo/owl";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.sequenceTooltip = useState({ value: "" });
    },
    getSequenceStage(line) {
        return line.product_id.pos_sequence_stage_ids;
    },
    toggleSequenceTooltip(line) {
        if (this.sequenceTooltip.value === line.uuid) {
            this.sequenceTooltip.value = "";
        } else {
            this.sequenceTooltip.value = line.uuid;
        }
    },
    selectSequenceStage(line, sequenceStage) {
        if (line.pos_sequence_stage_id === sequenceStage) {
            line.update({ pos_sequence_stage_id: null });
            return;
        }
        line.update({ pos_sequence_stage_id: sequenceStage });
    },
    get currentLines() {
        return this.currentOrder.lines.sort(
            (a, b) => a.pos_sequence_stage_id?.sequence - b.pos_sequence_stage_id?.sequence
        );
    },
});
