import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("Displays the table with details of the down payment", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const productDownPayment = store.models["product.template"].get(105);
    const sol1 = store.models["sale.order.line"].get(1);
    const sol2 = store.models["sale.order.line"].get(2);
    const line = await store.addLineToOrder(
        {
            product_tmpl_id: productDownPayment,
            sale_order_origin_id: 1,
            down_payment_details: [
                {
                    product_name: sol1.display_name,
                    product_uom_qty: sol1.product_uom_qty,
                    price_unit: sol1.price_unit,
                    total: sol1.price_total,
                },
                {
                    product_name: sol2.display_name,
                    product_uom_qty: sol2.product_uom_qty,
                    price_unit: sol2.price_unit,
                    total: sol2.price_total,
                },
            ],
            qty: 1,
        },
        order
    );

    const comp = await mountWithCleanup(Orderline, { props: { line } });

    const saleOrderInfo = ".orderline .info-list .sale-order-info";
    const cell = (tr, td) => `${saleOrderInfo} tr:nth-child(${tr}) td:nth-child(${td})`;

    expect(comp.line).toEqual(line);
    expect(saleOrderInfo).toBeVisible();
    expect(`${saleOrderInfo} tr`).toHaveCount(2);

    expect(cell(1, 1)).toHaveText("5x");
    expect(cell(1, 2)).toHaveText("Product 1");
    expect(cell(1, 4)).toHaveText(`$ 500.00 (tax incl.)`);

    expect(cell(2, 1)).toHaveText("3x");
    expect(cell(2, 2)).toHaveText("Product 2");
    expect(cell(2, 4)).toHaveText(`$ 150.00 (tax incl.)`);
});
