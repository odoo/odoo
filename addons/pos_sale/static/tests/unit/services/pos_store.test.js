import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { click, waitFor, waitUntil } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const createSaleOrderWithFixedTax = (store) => {
    const percentTax = store.models["account.tax"].create({
        name: "20% incl",
        amount_type: "percent",
        amount: 20,
        price_include: true,
        sequence: 1,
        tax_group_id: 1,
    });
    const fixedTax = store.models["account.tax"].create({
        name: "1 fixed incl",
        amount_type: "fixed",
        amount: 1,
        price_include: true,
        sequence: 1,
        tax_group_id: 1,
    });
    return store.models["sale.order"].create({
        name: "S00101",
        amount_unpaid: 100,
        order_line: [
            [
                "create",
                {
                    product_id: 5,
                    product_uom_qty: 1,
                    price_unit: 100,
                    price_total: 100,
                    discount: 0,
                    tax_ids: [["link", percentTax, fixedTax]],
                },
            ],
        ],
    });
};

describe("onClickSaleOrder", () => {
    test("no selection → abort", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const button =
            ".modal-header:has(.modal-title:contains('What do you want to do?')) button[aria-label='Close']";
        await waitFor(button);
        await click(button);

        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(2);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
    });

    test("settle → calls settleSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const button = ".modal-body button:contains('Settle the order')";
        await waitFor(button);
        await click(button);
        await promiseResult;

        const currentOrder = store.getOrder();

        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(4);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(5);
        expect(currentOrder.lines[2].qty).toBe(5);
        expect(currentOrder.lines[2].price_unit).toBe(100);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(500);

        expect(currentOrder.lines[3].product_id.id).toBe(6);
        expect(currentOrder.lines[3].qty).toBe(3);
        expect(currentOrder.lines[3].price_unit).toBe(50);
        expect(currentOrder.lines[3].prices.total_excluded).toBe(150);
    });

    test("dpPercentage → calls downPaymentSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const buttonDownPaymentPercentage =
            ".modal-body button:contains('Apply a down payment (percentage)')";
        await waitFor(buttonDownPaymentPercentage);
        await click(buttonDownPaymentPercentage);
        await waitFor(".modal-title:contains('Down Payment')");
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-footer .btn:contains('Apply')");
        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(3);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(105);
        expect(currentOrder.lines[2].qty).toBe(1);
        expect(currentOrder.lines[2].price_unit).toBe(325);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(325);

        const comp = await mountWithCleanup(Orderline, {
            props: { line: currentOrder.lines[2] },
        });

        const saleOrderInfo = ".orderline .info-list .sale-order-info";
        const cell = (tr, td) => `${saleOrderInfo} tr:nth-child(${tr}) td:nth-child(${td})`;

        expect(comp.line).toEqual(currentOrder.lines[2]);
        expect(`${saleOrderInfo} tr`).toHaveCount(4);

        expect(cell(1, 1)).toHaveText("5x");
        expect(cell(1, 2)).toHaveText("TEST");
        expect(cell(1, 4)).toHaveText(`$ 500.00 (tax incl.)`);

        expect(cell(2, 1)).toHaveText("3x");
        expect(cell(2, 2)).toHaveText("TEST 2");
        expect(cell(2, 4)).toHaveText(`$ 150.00 (tax incl.)`);
    });

    test("dpAmount → calls downPaymentSO", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        const promiseResult = store.onClickSaleOrder(1);
        const buttonDownPaymentPercentage =
            ".modal-body button:contains('Apply a down payment (fixed amount)')";
        await waitFor(buttonDownPaymentPercentage);
        await click(buttonDownPaymentPercentage);
        await waitFor(".modal-title:contains('Down Payment')");
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-footer .btn:contains('Apply')");
        await promiseResult;

        const currentOrder = store.getOrder();
        expect(currentOrder.id).toBe(order.id);
        expect(currentOrder.lines.length).toBe(3);

        expect(currentOrder.lines[0].product_id.id).toBe(5);
        expect(currentOrder.lines[0].qty).toBe(3);
        expect(currentOrder.lines[0].price_unit).toBe(3);
        expect(currentOrder.lines[0].prices.total_excluded).toBe(9);

        expect(currentOrder.lines[1].product_id.id).toBe(6);
        expect(currentOrder.lines[1].qty).toBe(2);
        expect(currentOrder.lines[1].price_unit).toBe(3);
        expect(currentOrder.lines[1].prices.total_excluded).toBe(6);

        expect(currentOrder.lines[2].product_id.id).toBe(105);
        expect(currentOrder.lines[2].qty).toBe(1);
        expect(currentOrder.lines[2].price_unit).toBe(50);
        expect(currentOrder.lines[2].prices.total_excluded).toBe(50);

        const comp = await mountWithCleanup(Orderline, {
            props: { line: currentOrder.lines[2] },
        });

        const saleOrderInfo = ".orderline .info-list .sale-order-info";
        const cell = (tr, td) => `${saleOrderInfo} tr:nth-child(${tr}) td:nth-child(${td})`;

        expect(comp.line).toEqual(currentOrder.lines[2]);
        expect(`${saleOrderInfo} tr`).toHaveCount(4);

        expect(cell(1, 1)).toHaveText("5x");
        expect(cell(1, 2)).toHaveText("TEST");
        expect(cell(1, 4)).toHaveText(`$ 500.00 (tax incl.)`);

        expect(cell(2, 1)).toHaveText("3x");
        expect(cell(2, 2)).toHaveText("TEST 2");
        expect(cell(2, 4)).toHaveText(`$ 150.00 (tax incl.)`);
    });

    test("import sale downpayment with percentage", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
        order.setOrderPrices();
        const original_price = order.amount_total;

        const promiseResult = store.onClickSaleOrder(3);
        const buttonDownPaymentPercentage =
            ".modal-body button:contains('Apply a down payment (percentage)')";
        await waitFor(buttonDownPaymentPercentage);
        await click(buttonDownPaymentPercentage);
        await waitFor(".modal-title:contains('Down Payment')");
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-body .numpad .numpad-button[value='+50']");
        await new Promise((resolve) => setTimeout(resolve, 50));
        await click(".modal-footer .btn:contains('Apply')");
        await promiseResult;

        const currentOrder = store.getOrder();
        currentOrder.setOrderPrices();
        expect(currentOrder.amount_total).toBe(
            650 - store.models["sale.order.line"].get(4).price_unit + original_price
        );
    });

    test("down payment line count on sale order with down payment", async () => {
        const store = await setupPosEnv();
        const currentOrder = store.getEmptyOrder();
        const saleOrder = await store._getSaleOrder(3);
        await store.addDownPaymentProductOrderlineToOrder(saleOrder, 20, "percentage");
        // This is required because we cannot await the for the order lines to be added in the pos order
        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(currentOrder.lines.length).toBe(1);
        expect(currentOrder.lines[0].price_unit).toBe(110);
    });

    test("percentage down payment popup shows the amount of the down payment line", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const saleOrder = createSaleOrderWithFixedTax(store);
        await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });

        // 50% of 99.00 (the order without its 1.00 fixed tax)
        const downPaymentAmount = 49.5;

        const downPaymentApplied = store.downPaymentSO(saleOrder, true);
        await waitFor(".modal-body .numpad");
        await click(".modal-body .numpad .numpad-button[value='5']");
        await click(".modal-body .numpad .numpad-button[value='0']");
        await waitFor(`.modal-body:contains('${downPaymentAmount.toFixed(2)}')`);
        await click(".modal-footer .btn:contains('Apply')");
        await downPaymentApplied;

        await waitUntil(() => order.lines.length === 1);
        const downPaymentLine = order.lines[0];
        expect(downPaymentLine.product_id.id).toBe(store.config.down_payment_product_id.id);
        expect(downPaymentLine.prices.total_included).toBe(downPaymentAmount);
    });

    test("second percentage down payment subtracts the exact amount of the first one", async () => {
        const store = await setupPosEnv();
        const saleOrder = createSaleOrderWithFixedTax(store);

        const firstPosDownPaymentOrder = store.addNewOrder();
        await store.addDownPaymentProductOrderlineToOrder(saleOrder, 50, true);
        await waitUntil(() => firstPosDownPaymentOrder.lines.length === 1);
        const firstDownPaymentLine = firstPosDownPaymentOrder.lines[0];
        expect(firstDownPaymentLine.product_id.id).toBe(store.config.down_payment_product_id.id);
        saleOrder.update({
            order_line: [
                [
                    "create",
                    {
                        is_downpayment: true,
                        product_id: firstDownPaymentLine.product_id,
                        product_uom_qty: 0,
                        price_unit: firstDownPaymentLine.price_unit,
                        tax_ids: [["link", ...firstDownPaymentLine.tax_ids]],
                        extra_tax_data: firstDownPaymentLine.extra_tax_data,
                    },
                ],
            ],
        });

        const secondPosDownPaymentOrder = store.addNewOrder();
        await store.addDownPaymentProductOrderlineToOrder(saleOrder, 50, true);
        await waitUntil(() => secondPosDownPaymentOrder.lines.length === 1);
        const secondDownPaymentLine = secondPosDownPaymentOrder.lines[0];
        expect(secondDownPaymentLine.product_id.id).toBe(store.config.down_payment_product_id.id);

        // 50% of (99.00 (the order without its 1.00 fixed tax) - 49.50 (the first down payment))
        const secondDownPaymentAmount = 24.75;
        expect(secondDownPaymentLine.prices.total_included).toBeCloseTo(secondDownPaymentAmount, {
            margin: 0.001,
        });
    });
});
