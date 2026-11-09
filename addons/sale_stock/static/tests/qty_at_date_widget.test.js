import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, mountView } from "@web/../tests/web_test_helpers";

class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _records = [
        { id: 1, name: "Units", factor: 1, rounding: 0.01 },
        { id: 2, name: "Dozens", factor: 12, rounding: 0.01 },
    ];
}

class ProductProduct extends models.ServerModel {
    _name = "product.product";

    _records = [{ id: 1, name: "Chair", uom_id: 1 }];
}

class StockMove extends models.ServerModel {
    _name = "stock.move";
}

class StockWarehouse extends models.ServerModel {
    _name = "stock.warehouse";
}

class SaleOrderLine extends models.ServerModel {
    _name = "sale.order.line";

    _records = [
        {
            id: 1,
            product_id: 1,
            product_uom_id: 1,
            state: "draft",
            display_qty_widget: true,
            scheduled_date: "2026-10-30 10:00:00",
            virtual_available_at_date: 5,
            free_qty_today: 5,
            qty_to_deliver: 1,
        },
        {
            id: 2,
            product_id: 1,
            product_uom_id: 2,
            state: "draft",
            display_qty_widget: true,
            scheduled_date: "2026-10-30 10:00:00",
            virtual_available_at_date: 2,
            free_qty_today: 2,
            qty_to_deliver: 1,
        },
    ];
}

defineModels([UomUom, ProductProduct, StockMove, StockWarehouse, SaleOrderLine]);
defineMailModels();

const arch = `
    <form>
        <field name="product_id"/>
        <field name="product_uom_id"/>
        <field name="state"/>
        <widget name="qty_at_date_widget"/>
    </form>`;

test("availability popover shows the unit of measure of the line", async () => {
    await mountView({ type: "form", resModel: "sale.order.line", resId: 1, arch });
    await contains(".fa-area-chart").click();
    expect(".popover tbody tr:first-child td:last-child").toHaveText("5 Units");
});

test("availability popover converts the quantity to the product unit of measure", async () => {
    await mountView({ type: "form", resModel: "sale.order.line", resId: 2, arch });
    await contains(".fa-area-chart").click();
    expect(".popover tbody tr:first-child td:last-child").toHaveText("2 Dozens\n24 Units");
});
