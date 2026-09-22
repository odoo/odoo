import { models } from "@web/../tests/web_test_helpers";

export class SaleOrderTemplate extends models.ServerModel {
    _name = "sale.order.template";

    _records = [1, 2, 3, 4].map((id) => ({
        id,
        name: `Section Template ${id}`,
        template_type: "section",
        user_has_access: true,
    }));

    prepare_section_template_order_lines() {
        return [
            {
                name: "Section Template 1",
                label: "Section Template 1",
                display_type: "line_section",
                product_uom_qty: 0,
                price_unit: 0,
                price_total: 0,
                price_subtotal: 0,
            },
            {
                name: "line1",
                label: "line1",
                product_uom_qty: 3,
                price_unit: 3,
                price_total: 9,
                price_subtotal: 9,
            },
            {
                name: "line2",
                label: "line2",
                product_uom_qty: 5,
                price_unit: 6,
                price_total: 7,
                price_subtotal: 8,
            },
        ];
    }
}
