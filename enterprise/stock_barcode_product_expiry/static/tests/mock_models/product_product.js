import { fields, models } from "@web/../tests/web_test_helpers";

export class ProductProduct extends models.Model {
    tracking = fields.Selection({
        selection: [
            ("serial", "By Unique Serial Number"),
            ("lot", "By Lots"),
            ("none", "By Quantity"),
        ],
    });
    use_expiration_date = fields.Boolean();
    is_storable = fields.Boolean();
    _records = [
        {
            id: 3,
            tracking: "lot",
            display_name: "test barcode",
            use_expiration_date: true,
            is_storable: true,
        },
    ];
}
