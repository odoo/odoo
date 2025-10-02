import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { click, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

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
        await click(".modal-footer .btn:contains('Ok')");
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
        await click(".modal-footer .btn:contains('Ok')");
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
});
