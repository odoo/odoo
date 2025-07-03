import { test, describe, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";

describe.current.tags("pos");
describe("pos.order", () => {
    test("uiState", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        expect(order.uiState).toEqual({
            unmerge: {},
            lastPrint: false,
            lineToRefund: {},
            displayed: true,
            booked: false,
            screen_data: {},
            selected_orderline_uuid: undefined,
            selected_paymentline_uuid: undefined,
            locked: false,
            TipScreen: {
                inputTipAmount: "",
            },
        });
    });

    test("totalQuantity", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        expect(order.totalQuantity).toBe(5);
    });

    test("setPreset", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const inPreset = store.models["pos.preset"].get(1);
        const outPreset = store.models["pos.preset"].get(2);

        expect(order.pricelist_id).toBe(inPreset.pricelist_id);
        expect(order.fiscal_position_id).toBe(inPreset.fiscal_position_id);

        order.setPreset(outPreset);

        expect(order.pricelist_id).toBe(outPreset.pricelist_id);
        expect(order.fiscal_position_id).toBe(outPreset.fiscal_position_id);

        order.setPreset(inPreset);

        expect(order.pricelist_id).toBe(inPreset.pricelist_id);
        expect(order.fiscal_position_id).toBe(inPreset.fiscal_position_id);
    });

    test("getTaxTotalsOfLines", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);
        const product2 = store.models["product.template"].get(6);

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
            },
            order
        );
        await store.addLineToOrder(
            {
                product_tmpl_id: product2,
                qty: 1,
            },
            order
        );

        // With pricelist prices are at 3 each
        const taxTotalsWPricelist = order.getTaxTotalsOfLines(order.lines);
        expect(taxTotalsWPricelist.base_amount).toBe(6);
        expect(taxTotalsWPricelist.total_amount).toBe(7.2);
        expect(taxTotalsWPricelist.tax_amount_currency).toBe(1.2);
        expect(taxTotalsWPricelist.subtotals[0].tax_groups[0].involved_tax_ids).toEqual([
            product.taxes_id[0].id,
            product2.taxes_id[0].id,
        ]);

        // Without pricelist prices are at 100 each
        order.setPricelist(null);
        const taxTotals = order.getTaxTotalsOfLines(order.lines);
        expect(taxTotals.base_amount).toBe(200);
        expect(taxTotals.total_amount).toBe(240); // Tax of 15% and 25% on 100 each
        expect(taxTotals.tax_amount_currency).toBe(40);
        expect(taxTotals.subtotals[0].tax_groups[0].involved_tax_ids).toEqual([
            product.taxes_id[0].id,
            product2.taxes_id[0].id,
        ]);
    });
});
