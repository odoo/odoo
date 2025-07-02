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

    test("priceDoesntChangeWhenChangingPreset", async () => {
        const store = await setupPosEnv();
        const outPreset = store.models["pos.preset"].get(2);

        const lines = store.models.loadConnectedData({
            "product.template": [
                {
                    id: 555,
                    name: "Test Combo Product Template",
                    combo_ids: [123],
                    product_variant_ids: [7],
                    taxes_id: [],
                },
            ],
            "product.combo.item": [
                {
                    id: 111,
                    combo_id: 123,
                    product_id: 5,
                    extra_price: 0,
                },
                {
                    id: 222,
                    combo_id: 123,
                    product_id: 6,
                    extra_price: 0,
                },
                {
                    id: 333,
                    combo_id: 123,
                    product_id: 6,
                    extra_price: 5,
                },
            ],
            "product.combo": [
                {
                    id: 123,
                    name: "Test Combo",
                    qty_max: 4,
                    qty_free: 2,
                    base_price: 10,
                    combo_item_ids: [111, 222, 333],
                },
            ],
            "product.product": [
                {
                    id: 7,
                    display_name: "Test Combo Product",
                    product_tmpl_id: 555,
                    lst_price: 10,
                    combo_ids: [1],
                },
            ],
            "pos.order": [
                {
                    id: 1,
                    name: "Test Order extra qty",
                },
                {
                    id: 2,
                    name: "Test Order normal",
                },
                {
                    id: 3,
                    name: "Test Order extra price",
                },
                {
                    id: 4,
                    name: "Test Order all the same products",
                },
            ],
        });
        // Same taxes_id for every product
        store.models["product.product"].get(6).taxes_id = [1];

        // Normal flow with extras
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 2 }],
                    [{ combo_item_id: store.models["product.combo.item"].get(222), qty: 2 }],
                ],
                qty: 1,
            },
            lines["pos.order"][0]
        );
        expect(lines["pos.order"][0].amount_total).toBe(34.5);
        lines["pos.order"][0].setPreset(outPreset);
        lines["pos.order"][0].recomputeOrderData();
        expect(lines["pos.order"][0].amount_total).toBe(34.5);

        // Normal flow
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [[{ combo_item_id: store.models["product.combo.item"].get(111), qty: 2 }]],
                qty: 1,
            },
            lines["pos.order"][1]
        );
        expect(lines["pos.order"][1].amount_total).toBe(11.5);
        lines["pos.order"][1].setPreset(outPreset);
        lines["pos.order"][1].recomputeOrderData();
        expect(lines["pos.order"][1].amount_total).toBe(11.5);

        // Flow with products with extra price
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 2 }],
                    [{ combo_item_id: store.models["product.combo.item"].get(333), qty: 2 }],
                ],
                qty: 1,
            },
            lines["pos.order"][2]
        );
        expect(lines["pos.order"][2].amount_total).toBe(46);
        lines["pos.order"][2].setPreset(outPreset);
        lines["pos.order"][2].recomputeOrderData();
        expect(lines["pos.order"][2].amount_total).toBe(46);

        // Flow with all the same product
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 2 }],
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 2 }],
                ],
                qty: 1,
            },
            lines["pos.order"][3]
        );
        expect(lines["pos.order"][3].amount_total).toBe(34.5);
        lines["pos.order"][3].setPreset(outPreset);
        lines["pos.order"][3].recomputeOrderData();
        expect(lines["pos.order"][3].amount_total).toBe(34.5);
    });
});
