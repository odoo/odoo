import { models } from "@web/../tests/web_test_helpers";
import { isIterable } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class PosOrderLine extends models.ServerModel {
    _name = "pos.order.line";

    create() {
        const orderLine = super.create(...arguments);
        this.write(isIterable(orderLine) ? orderLine : [orderLine], {
            write_date: DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss"),
        });
        return orderLine;
    }

    _load_pos_data_fields() {
        return [
            "qty",
            "attribute_value_ids",
            "custom_attribute_value_ids",
            "price_unit",
            "uuid",
            "price_subtotal",
            "price_subtotal_incl",
            "order_id",
            "note",
            "prep_line_ids",
            "price_type",
            "product_id",
            "discount",
            "tax_ids",
            "customer_note",
            "refunded_qty",
            "price_extra",
            "full_product_name",
            "refunded_orderline_id",
            "combo_parent_id",
            "combo_line_ids",
            "combo_item_id",
            "refund_orderline_ids",
            "extra_tax_data",
            "write_date",
        ];
    }
}
