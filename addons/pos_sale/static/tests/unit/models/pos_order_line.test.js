import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("saleDetails", () => {
    test("down payment details as array", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        const productDownPayment = store.models["product.template"].get(105);
        const line = await store.addLineToOrder(
            {
                product_tmpl_id: productDownPayment,
                down_payment_details: [
                    {
                        product_name: "Product 1",
                        product_uom_qty: 2,
                        total: 100,
                    },
                    {
                        product_name: "Product 2",
                        product_uom_qty: 1,
                        total: 50,
                    },
                ],
                qty: 1,
            },
            order
        );

        const saleDetails = line.saleDetails;
        expect(saleDetails).toEqual([
            {
                product_uom_qty: 2,
                product_name: "Product 1",
                total: "$\u00a0100.00",
            },
            {
                product_uom_qty: 1,
                product_name: "Product 2",
                total: "$\u00a050.00",
            },
        ]);
    });

    test("down payment details as stringified JSON", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        const productDownPayment = store.models["product.template"].get(105);
        const line = await store.addLineToOrder(
            {
                product_tmpl_id: productDownPayment,
                down_payment_details: JSON.stringify([
                    {
                        product_name: "Product 1",
                        product_uom_qty: 2,
                        total: 100,
                    },
                    {
                        product_name: "Product 2",
                        product_uom_qty: 1,
                        total: 50,
                    },
                ]),
                qty: 1,
            },
            order
        );

        const saleDetails = line.saleDetails;
        expect(saleDetails).toEqual([
            {
                product_uom_qty: 2,
                product_name: "Product 1",
                total: "$\u00a0100.00",
            },
            {
                product_uom_qty: 1,
                product_name: "Product 2",
                total: "$\u00a050.00",
            },
        ]);
    });
});

describe("setQuantityFromSOL", () => {
    test("service product, state != sent/draft → qty_to_invoice", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const line = order.lines[0];
        line.product_id.type = "service";
        line.sale_order_origin_id = { state: "sale" }; // not 'sent' or 'draft'

        const saleOrderLine = { qty_to_invoice: 2 };

        await line.setQuantityFromSOL(saleOrderLine);
        expect(line.qty).toBe(2);
    });

    test("non-service product → qty = uom_qty - max(delivered, invoiced)", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const line = order.lines[0];
        line.product_id.type = "consu";

        const saleOrderLine = {
            product_uom_qty: 8,
            qty_delivered: 1,
            qty_invoiced: 2,
        };

        await line.setQuantityFromSOL(saleOrderLine);
        expect(line.qty).toBe(6); // 8 - max(1,2)
    });
});
