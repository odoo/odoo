import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class SaleOrder extends models.ServerModel {
    _name = "sale.order";

    _load_pos_data_fields() {
        return [
            "name",
            "state",
            "user_id",
            "order_line",
            "partner_id",
            "pricelist_id",
            "fiscal_position_id",
            "amount_total",
            "amount_untaxed",
            "amount_unpaid",
            "picking_ids",
            "partner_shipping_id",
            "partner_invoice_id",
            "date_order",
            "write_date",
        ];
    }

    _records = [
        {
            id: 1,
            name: "S00001",
            state: "sale",
            order_line: [1, 2],
            partner_id: 3,
            pricelist_id: 1,
            fiscal_position_id: 1,
            amount_total: 650,
            amount_untaxed: 500,
            amount_unpaid: 650,
            partner_shipping_id: 3,
            partner_invoice_id: 3,
            date_order: "2025-07-03 17:04:14",
            write_date: "2025-07-03 17:04:14",
        },
    ];

    async load_sale_order_from_pos(id, config_id) {
        const order = this.env["sale.order"].find((order) => order.id === id);
        const orderLines = this.env["sale.order.line"].filter((line) =>
            order.order_line.includes(line.id)
        );
        const partner = this.env["res.partner"].find((partner) => partner.id === order.partner_id);
        const productProducts = this.env["product.product"].filter((product) =>
            orderLines.map((line) => line.product_id).includes(product.id)
        );
        const productTemplates = this.env["product.template"].filter((template) =>
            productProducts.map((p) => p.product_tmpl_id).includes(template.id)
        );
        return {
            "sale.order": [order],
            "sale.order.line": orderLines,
            "res.partner": [partner],
            "product.product": productProducts,
            "product.template": productTemplates,
        };
    }
}

patch(hootPosModels, [...hootPosModels, SaleOrder]);
