import { models } from "@web/../tests/web_test_helpers";

export class SaleOrderTemplate extends models.ServerModel {
    _name = "sale.order.template";

    get_section_templates() {
        return [
            {
                id: 1,
                name: "Section Template 1",
                create_uid: this.env.user.id,
            },
            {
                id: 2,
                name: "Section Template 2",
                create_uid: this.env.user.id,
            },
            {
                id: 3,
                name: "Section Template 3",
                create_uid: this.env.user.id,
            },
            {
                id: 4,
                name: "Section Template 4",
                create_uid: this.env.user.id,
            },
        ];
    }

    prepare_section_template_order_lines() {
        return [
            {
                name: "Section Template 1",
                display_type: "line_section",
                product_uom_qty: 0,
                price_unit: 0,
                price_total: 0,
                price_subtotal: 0,
            },
            {
                name: "line1",
                product_uom_qty: 3,
                price_unit: 3,
                price_total: 9,
                price_subtotal: 9,
            },
            {
                name: "line2",
                product_uom_qty: 5,
                price_unit: 6,
                price_total: 7,
                price_subtotal: 8,
            },
        ];
    }
}
