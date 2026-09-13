import { models } from "@web/../tests/web_test_helpers";

export class PosPrepOrder extends models.ServerModel {
    _name = "pos.prep.order";

    _load_pos_data_fields() {
        return [];
    }

    update_last_order_change(orderId) {
        const [order] = this.env["pos.order"].read([orderId], ["lines"], false);
        const lines = this.env["pos.order.line"].read(
            order.lines,
            ["qty", "product_id", "attribute_value_ids", "prep_line_ids"],
            false
        );
        let prepOrderId = false;

        for (const line of lines) {
            const prepLines = this.env["pos.prep.line"].read(
                line.prep_line_ids,
                ["quantity", "cancelled"],
                false
            );
            const prepQty = prepLines.reduce((qty, pl) => qty + pl.quantity - pl.cancelled, 0);
            const quantityDiff = line.qty - prepQty;

            if (quantityDiff <= 0) {
                continue;
            }

            prepOrderId ||= this.create({ pos_order_id: orderId });
            this.env["pos.prep.line"].create({
                prep_order_id: prepOrderId,
                pos_order_line_id: line.id,
                product_id: line.product_id,
                quantity: quantityDiff,
                cancelled: 0,
                attribute_value_ids: line.attribute_value_ids,
            });
        }

        return prepOrderId;
    }
}
