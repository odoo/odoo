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

    test("updatePricelistAndFiscalPosition", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const partner = models["res.partner"].get(3);

        partner.fiscal_position_id = models["account.fiscal.position"].get(1);
        partner.property_product_pricelist = models["product.pricelist"].get(1);

        const order = store.addNewOrder();
        order.preset_id = null;
        order.updatePricelistAndFiscalPosition(partner);

        expect(order.fiscal_position_id.id).toBe(partner.fiscal_position_id.id);
        expect(order.pricelist_id.id).toBe(partner.property_product_pricelist.id);
    });
});
