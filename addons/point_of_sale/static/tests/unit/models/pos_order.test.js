import { test, describe, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

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

    test("updateLastOrderChange", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.setGeneralCustomerNote("Customer note");
        order.setInternalNote("Internal note");
        order.updateLastOrderChange();
        expect(order.last_order_preparation_change.general_customer_note).toBe("Customer note");
        expect(order.last_order_preparation_change.internal_note).toBe("Internal note");
    });

    test("removeOrderline", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.general_customer_note = "Some note";
        const line1 = order.lines[0];
        const line2 = order.lines[1];
        expect(order.getSelectedOrderline()).toBe(line2);
        order.removeOrderline(line2);
        expect(order.general_customer_note).toBe("Some note");
        expect(order.getSelectedOrderline()).toBe(line1);
        order.removeOrderline(line1);
        // General customer note should be removed when removing the last order line
        expect(order.general_customer_note).toBe("");
    });

    test("addPaymentline", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const cashPaymentMethod = store.models["pos.payment.method"].get(1);
        // Test that the payment line is correctly created
        const result = order.addPaymentline(cashPaymentMethod);
        expect(result.payment_method_id.id).toBe(cashPaymentMethod.id);
        expect(result.amount).toBe(17.85);
    });

    test("getTotalDiscount", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const discount = order.getTotalDiscount();
        expect(discount).toBe(0);
        const taxTotals = order.getTaxTotalsOfLines(order.lines);
        expect(taxTotals.base_amount).toBe(15);
        expect(taxTotals.total_amount).toBe(17.85);
        expect(taxTotals.tax_amount_currency).toBe(2.85);

        //Compute total of discount on the order
        const line1 = order.lines[0];
        const line2 = order.lines[1];
        line1.setDiscount(20);
        line2.setDiscount(50);
        expect(order.getTotalDiscount()).toBe(5.82);
        const taxTotalsWDiscount = order.getTaxTotalsOfLines(order.lines);
        expect(taxTotalsWDiscount.base_amount).toBe(10.2);
        expect(taxTotalsWDiscount.total_amount).toBe(12.03);
        expect(taxTotalsWDiscount.tax_amount_currency).toBe(1.83);
    });

    test("preventRoundingErrorsCombo", async () => {
        const store = await setupPosEnv();

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
                    extra_price: 0,
                },
            ],
            "product.combo": [
                {
                    id: 123,
                    name: "Test Combo",
                    qty_max: 6,
                    qty_free: 3,
                    base_price: 20,
                    combo_item_ids: [111, 222, 333],
                },
            ],
            "product.product": [
                {
                    id: 7,
                    display_name: "Test Combo Product",
                    product_tmpl_id: 555,
                    lst_price: 50,
                    combo_ids: [1],
                },
            ],
            "pos.order": [
                {
                    id: 1,
                    name: "Test Order",
                },
                {
                    id: 2,
                    name: "Test Order 2",
                },
                {
                    id: 3,
                    name: "Test Order 3",
                },
            ],
        });
        // Same taxes for every product
        store.models["product.product"].get(6).taxes_id = [1];

        // 3 of the same product
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [[{ combo_item_id: store.models["product.combo.item"].get(111), qty: 3 }]],
                qty: 1,
            },
            lines["pos.order"][0]
        );
        expect(lines["pos.order"][0].amount_total).toBe(57.5);
        expect(lines["pos.order"][0].lines[1].qty).toBe(3);
        expect(lines["pos.order"][0].lines[1].price_unit).toBe(50 / 3);

        // 3 different products
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [
                    [
                        { combo_item_id: store.models["product.combo.item"].get(111), qty: 1 },
                        { combo_item_id: store.models["product.combo.item"].get(222), qty: 1 },
                        { combo_item_id: store.models["product.combo.item"].get(333), qty: 1 },
                    ],
                ],
                qty: 1,
            },
            lines["pos.order"][1]
        );
        expect(lines["pos.order"][1].amount_total).toBe(57.5);
        expect(lines["pos.order"][1].lines[1].price_unit).toBe(16.67);
        expect(lines["pos.order"][1].lines[2].price_unit).toBe(16.67);
        expect(lines["pos.order"][1].lines[3].price_unit).toBe(16.659999999999997);

        // 3 of the same product and 3 of the same extra items
        await store.addLineToOrder(
            {
                product_tmpl_id: store.models["product.template"].get(555),
                payload: [
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 3 }],
                    [{ combo_item_id: store.models["product.combo.item"].get(111), qty: 3 }],
                ],
                qty: 1,
            },
            lines["pos.order"][2]
        );
        expect(lines["pos.order"][2].amount_total).toBe(126.5);
        expect(lines["pos.order"][2].lines[1].qty).toBe(3);
        expect(lines["pos.order"][2].lines[1].price_unit).toBe(50 / 3);
        expect(lines["pos.order"][2].lines[2].qty).toBe(3);
        expect(lines["pos.order"][2].lines[2].price_unit).toBe(20);
    });
});
