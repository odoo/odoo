import { defineModels, fields, models } from "@web/../tests/web_test_helpers";
import { SpreadsheetMixin } from "@spreadsheet/../tests/helpers/data";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/helpers/mock_server";

export class SaleOrder extends models.Model {
    _name = "sale.order";

    _records = [{ id: 1 }];
}

export class SaleOrderLine extends models.Model {
    _name = "sale.order.line";

    name = fields.Char();
    order_id = fields.Many2one({ relation: "sale.order" });
    product_id = fields.Many2one({ relation: "product" });
    product_uom_qty = fields.Float();
    qty_delivered = fields.Float();

    _records = [{ id: 1, order_id: 1, product_id: 1 }];
}

export class Product extends models.Model {
    _name = "product";

    name = fields.Char();

    _records = [{ id: 1, name: "Chair" }];
}

export class SaleOrderSpreadsheet extends SpreadsheetMixin {
    _name = "sale.order.spreadsheet";

    name = fields.Char();
    order_id = fields.Many2one({ relation: "sale.order" });

    _records = [
        {
            id: 1,
            name: "My sale order spreadsheet",
            order_id: 1,
            spreadsheet_data: JSON.stringify(getSaleOrderSpreadsheetData()),
        },
    ];

    join_spreadsheet_session(resId, shareId, accessToken) {
        const result = mockJoinSpreadsheetSession(this._name).call(
            this,
            resId,
            shareId,
            accessToken
        );
        const order = this.env["sale.order"].find((r) => r.id === this[0].order_id);
        if (order) {
            result.order_id = order.id;
            result.order_display_name = order.display_name;
        }
        return result;
    }

    dispatch_spreadsheet_message() {}
}

export function defineSpreadsheetSaleModels() {
    defineModels({
        SaleOrder,
        Product,
        SaleOrderLine,
        SaleOrderSpreadsheet,
    });
}

const SALE_ORDER_LINE_FIELDS = [
    "product_id",
    "product_uom_qty",
    "qty_delivered",
    "qty_invoiced",
    "qty_to_invoice",
    "product_uom",
    "price_unit",
    "price_tax",
    "price_subtotal",
];

export function getSaleOrderSpreadsheetData() {
    return {
        revisionId: "START_REVISION",
        sheets: [{ id: "sheet1" }],
        lists: {
            1: {
                columns: SALE_ORDER_LINE_FIELDS,
                domain: [],
                model: "sale.order.line",
                context: {},
                orderBy: [],
                id: "1",
                name: "Sale order lines",
                fieldMatching: {
                    order_filter_id: {
                        chain: "order_id",
                        type: "many2one",
                    },
                },
            },
        },
        globalFilters: [
            {
                id: "order_filter_id",
                type: "relation",
                label: "Sales Order",
                modelName: "sale.order",
            },
        ],
    };
}
