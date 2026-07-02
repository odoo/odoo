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
            "partner_shipping_id",
            "partner_invoice_id",
            "transaction_ids",
            "date_order",
            "write_date",
        ];
    }

    _records = [
        {
            id: 1,
            name: "S00001",
            state: "sale",
            order_line: [1, 2, 7],
            partner_id: 3,
            pricelist_id: 1,
            fiscal_position_id: 1,
            amount_total: 650,
            amount_untaxed: 500,
            amount_unpaid: 650,
            partner_shipping_id: 3,
            partner_invoice_id: 3,
            transaction_ids: [],
            date_order: "2025-07-03 17:04:14",
            write_date: "2025-07-03 17:04:14",
        },
        {
            id: 2,
            name: "S00002",
            state: "sale",
            order_line: [3, 4],
            partner_id: 3,
            pricelist_id: 1,
            fiscal_position_id: 1,
            amount_total: 650,
            amount_untaxed: 650,
            amount_unpaid: 500,
            partner_shipping_id: 3,
            partner_invoice_id: 3,
            transaction_ids: [],
            date_order: "2025-07-03 17:04:14",
            write_date: "2025-07-03 17:04:14",
        },
        {
            id: 4,
            name: "S00004",
            state: "sale",
            order_line: [1, 2, 6],
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
        const getRecords = (modelName, recIds) =>
            this.env[modelName].filter((rec) => recIds.includes(rec.id));

        const orderLines = getRecords("sale.order.line", order.order_line);
        const productProducts = getRecords(
            "product.product",
            orderLines.map((line) => line.product_id)
        );
        const transactions = getRecords("payment.transaction", order.transaction_ids);
        return {
            "sale.order": [order],
            "sale.order.line": orderLines,
            "res.partner": getRecords("res.partner", [order.partner_id]),
            "product.product": productProducts,
            "product.template": getRecords(
                "product.template",
                productProducts.map((p) => p.product_tmpl_id)
            ),
            "payment.transaction": transactions,
            "account.payment": getRecords(
                "account.payment",
                transactions.map((txn) => txn.payment_id)
            ),
        };
    }
}

patch(hootPosModels, [...hootPosModels, SaleOrder]);
