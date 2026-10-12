import { fields, models } from "@web/../tests/web_test_helpers";

export class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    label = fields.Text({ compute: "_computeLabel", readonly: false });

    // directly set `name` to `label` to avoid complications with `display_name`
    _computeLabel() {
        for (const record of this) {
            record.label = record.name;
        }
    }
}
