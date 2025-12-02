import { models } from "@web/../tests/web_test_helpers";

export class PosOrderLine extends models.ServerModel {
    _name = "pos.order.line";

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
            "price_type",
            "product_id",
            "discount",
            "tax_ids",
            "pack_lot_ids",
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
