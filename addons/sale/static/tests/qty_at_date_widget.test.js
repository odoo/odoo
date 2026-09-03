import { expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, models, mountView } from "@web/../tests/web_test_helpers";
import { saleModels } from "./sale_test_helpers";

class ProductProduct extends saleModels.ProductProduct {
    _records = [
        { id: 1, name: "Test Product", uom_id: 1 }
    ];
}

class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _records = [
        { id: 1, name: "Units", factor: 1.0 },
        { id: 2, name: "Pack of 6", factor: 6.0 },
    ];
}

class SaleOrderLine extends saleModels.SaleOrderLine {
    _records = [
        {
            // 3 packs of 6 = 18 units, more than the 12 units available: should be flagged
            id: 1,
            product_id: 1,
            product_uom_id: 2,
            product_uom_qty: 3,
            qty_delivered: 0,
            display_qty_widget: true,
            virtual_available_at_date: 12,
            qty_available_today: 12,
        },
        {
            // 3 units, the product's own uom: within the 12 units available
            id: 2,
            product_id: 1,
            product_uom_id: 1,
            product_uom_qty: 3,
            qty_delivered: 0,
            display_qty_widget: true,
            virtual_available_at_date: 12,
            qty_available_today: 12,
        },
    ];
}

defineModels({ ...saleModels, ProductProduct, SaleOrderLine, UomUom });

test("qty at date widget converts the ordered qty to the product's uom before comparing to the forecast", async () => {
    await mountView({
        resModel: "sale.order.line",
        type: "list",
        arch: `
            <list>
                <field name="product_id" column_invisible="1"/>
                <field name="product_uom_qty" column_invisible="1"/>
                <field name="product_uom_id" column_invisible="1"/>
                <field name="qty_delivered" column_invisible="1"/>
                <widget name="simple_qty_at_date_widget"/>
            </list>
        `,
    });
    await animationFrame();

    const [shortageRow, sufficientRow] = queryAll(".o_data_row");
    expect(queryOne(".fa-area-chart", { root: shortageRow })).toHaveClass("text-danger", {
        message: "3 packs of 6 (18 units) exceed the 12 units available in stock",
    });
    expect(queryOne(".fa-area-chart", { root: sufficientRow })).not.toHaveClass("text-danger", {
        message: "3 units are within the 12 units available in stock",
    });
});
