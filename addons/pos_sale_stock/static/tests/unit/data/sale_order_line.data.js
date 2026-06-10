import { patch } from "@web/core/utils/patch";
import { SaleOrderLine } from "@pos_sale/../tests/unit/data/sale_order_line.data";

const POS_SALE_STOCK_LOT_METADATA = {
    31: { lot_names: ["1001", "1002"], lot_qty_by_name: { 1001: 1, 1002: 1 } },
    32: { lot_names: ["LOT-1", "LOT-2"], lot_qty_by_name: { "LOT-1": 2, "LOT-2": 1 } },
    33: { lot_names: ["LOT-PRICE"], lot_qty_by_name: { "LOT-PRICE": 1 } },
};

SaleOrderLine._records = [
    ...SaleOrderLine._records,
    {
        id: 31,
        display_name: "Serial SO Product",
        product_id: 27,
        product_uom_qty: 2,
        order_id: 31,
        price_unit: 8,
        price_total: 16,
        discount: 0,
        qty_delivered: 0,
        qty_invoiced: 0,
        qty_to_invoice: 2,
        display_type: false,
        name: "Serial SO Product",
        tax_ids: [],
        is_downpayment: false,
        extra_tax_data: {},
        write_date: "2025-07-03 17:04:14",
    },
    {
        id: 32,
        display_name: "Lot Non Groupable SO Product",
        product_id: 26,
        product_uom_qty: 3,
        order_id: 32,
        price_unit: 12,
        price_total: 36,
        discount: 15,
        qty_delivered: 0,
        qty_invoiced: 0,
        qty_to_invoice: 3,
        display_type: false,
        name: "Lot Non Groupable SO Product",
        tax_ids: [],
        is_downpayment: false,
        extra_tax_data: {},
        write_date: "2025-07-03 17:04:14",
    },
    {
        id: 33,
        display_name: "Lot Price SO Product",
        product_id: 26,
        product_uom_qty: 1,
        order_id: 33,
        price_unit: 120,
        price_total: 120,
        discount: 0,
        qty_delivered: 0,
        qty_invoiced: 0,
        qty_to_invoice: 1,
        display_type: false,
        name: "Lot Price SO Product",
        tax_ids: [],
        is_downpayment: false,
        extra_tax_data: {},
        write_date: "2025-07-03 17:04:14",
    },
];

patch(SaleOrderLine.prototype, {
    async read_converted(ids) {
        const records = await super.read_converted(...arguments);
        return records.map((record) => ({
            ...record,
            ...(POS_SALE_STOCK_LOT_METADATA[record.id] || {}),
        }));
    },
});
