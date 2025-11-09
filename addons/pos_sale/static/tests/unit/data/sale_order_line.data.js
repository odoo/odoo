import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models, MockServer } from "@web/../tests/web_test_helpers";

export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    _load_pos_data_fields() {
        return [
            "discount",
            "display_name",
            "price_total",
            "price_unit",
            "product_id",
            "product_uom_qty",
            "qty_delivered",
            "qty_invoiced",
            "qty_to_invoice",
            "display_type",
            "name",
            "tax_ids",
            "is_downpayment",
            "extra_tax_data",
            "write_date",
            "is_repair_line",
        ];
    }

    _records = [
        {
            id: 1,
            display_name: "Product 1",
            product_id: 5,
            product_uom_qty: 5,
            price_unit: 100,
            price_total: 500,
            discount: 0,
            qty_delivered: 0,
            qty_invoiced: 0,
            qty_to_invoice: 5,
            display_type: false,
            name: "Product 1",
            tax_ids: [],
            is_downpayment: false,
            extra_tax_data: {},
            write_date: "2025-07-03 17:04:14",
        },
        {
            id: 2,
            display_name: "Product 2",
            product_id: 6,
            product_uom_qty: 3,
            price_unit: 50,
            price_total: 150,
            discount: 0,
            qty_delivered: 0,
            qty_invoiced: 0,
            qty_to_invoice: 3,
            display_type: false,
            name: "Product 2",
            tax_ids: [],
            is_downpayment: false,
            extra_tax_data: {},
            write_date: "2025-07-03 17:04:14",
        },
    ];

    async read_converted(ids) {
        const model = MockServer.env[this._name];
        const posFields = model._load_pos_data_fields();
        const records = model.search_read(
            [["id", "in", ids]],
            posFields,
            false,
            false,
            false,
            false
        );
        return records;
    }
}

patch(hootPosModels, [...hootPosModels, SaleOrderLine]);
