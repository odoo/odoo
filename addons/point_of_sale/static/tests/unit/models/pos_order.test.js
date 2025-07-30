import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

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
        requiredPartnerDetails: {},
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
    store.models["product.product"].get(7).taxes_id = [1];
    store.models["product.product"].get(7).lst_price = 50;
    store.models["product.product"].get(8).taxes_id = [1];
    store.models["product.product"].get(9).taxes_id = [1];
    store.models["pos.preset"].get(1).pricelist_id = false;
    store.models["product.combo"].get(1).qty_free = 3;
    store.models["product.combo"].get(1).base_price = 10;
    const comboProduct1 = store.models["product.combo.item"].get(1);
    const comboProduct2 = store.models["product.combo.item"].get(2);
    comboProduct2.extra_price = 0;
    const template = store.models["product.template"].get(7);
    const order = store.addNewOrder();
    const order2 = store.addNewOrder();
    const order3 = store.addNewOrder();

    // 3 of the same product
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [[{ combo_item_id: comboProduct1, qty: 3 }]],
            qty: 1,
        },
        order
    );
    expect(order.amount_total).toBe(57.5);
    expect(order.lines[1].qty).toBe(2);
    expect(order.lines[1].price_unit).toBe(16.67);
    expect(order.lines[2].qty).toBe(1);
    expect(Math.round(order.lines[2].price_unit * 100) / 100).toBe(16.66);

    // 2 different products
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [
                    { combo_item_id: comboProduct1, qty: 1 },
                    { combo_item_id: comboProduct2, qty: 2 },
                ],
            ],
            qty: 1,
        },
        order2
    );
    expect(order2.amount_total).toBe(57.5);
    expect(order2.lines[1].price_unit).toBe(16.67);
    expect(order2.lines[1].qty).toBe(1);
    expect(order2.lines[2].price_unit).toBe(16.67);
    expect(order2.lines[2].qty).toBe(1);
    expect(Math.round(order2.lines[3].price_unit * 100) / 100).toBe(16.66);
    expect(order2.lines[3].qty).toBe(1);

    // 3 of the same product and 3 of the same extra items
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboProduct1, qty: 3 }],
                [{ combo_item_id: comboProduct1, qty: 3 }],
            ],
            qty: 1,
        },
        order3
    );
    expect(order3.amount_total).toBe(92);
    expect(order3.lines[1].qty).toBe(2);
    expect(order3.lines[1].price_unit).toBe(16.67);
    expect(Math.round(order3.lines[2].price_unit * 100) / 100).toBe(16.66);
    expect(order3.lines[2].qty).toBe(1);
    expect(order3.lines[3].qty).toBe(3);
    expect(order3.lines[3].price_unit).toBe(10);
});

test("customer requirements", async () => {
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(3); // Address Required Preset
    const partner = store.models["res.partner"].get(3); // Customer Without Address
    const order = store.addNewOrder();
    order.preset_id = preset;

    // No partner
    expect(order.presetRequirementsFilled).toBe(false);
    expect(order.uiState.requiredPartnerDetails.field).toBe("Customer");
    expect(order.uiState.requiredPartnerDetails.message).toBe(
        "Please add a valid customer to the order."
    );

    // Partner
    order.partner_id = partner;
    expect(order.presetRequirementsFilled).toBe(true);
});

test("Address requirements", async () => {
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(4); // Address Required Preset
    const partner = store.models["res.partner"].get(3); // Customer Without Address
    const order = store.addNewOrder();
    order.preset_id = preset;
    order.partner_id = partner;

    expect(order.presetRequirementsFilled).toBe(false);
    expect(order.uiState.requiredPartnerDetails.field).toBe("Address");
    expect(order.uiState.requiredPartnerDetails.message).toBe(
        "The selected customer needs an address."
    );

    // Partner with address
    partner.street = "test abc";
    expect(order.presetRequirementsFilled).toBe(true);
});

test("slot requirement preset", async () => {
    const store = await setupPosEnv();
    const preset = store.models["pos.preset"].get(2); // Time Slot Preset
    const order = store.addNewOrder();
    order.preset_id = preset;

    // No slot
    expect(order.presetRequirementsFilled).toBe(false);
    expect(order.uiState.requiredPartnerDetails.field).toBe("Slot");
    expect(order.uiState.requiredPartnerDetails.message).toBe(
        "Please select a time slot before proceeding."
    );

    // Slot set
    order.preset_time = "2025-08-11 14:00:00";
    expect(order.presetRequirementsFilled).toBe(true);
});

test("setShippingDate and getShippingDate with Luxon", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const testDate = "2019-03-11";
    order.setShippingDate(testDate);

    expect(order.shipping_date.toISODate()).toBe(testDate);
    expect(typeof order.getShippingDate()).toBe("string");
    order.setShippingDate(null);
    expect(order.getShippingDate()).toBeEmpty();
});

test("priceDoesntChangeWhenChangingPreset", async () => {
    const store = await setupPosEnv();
    store.models["pos.preset"].get(1).pricelist_id = false;
    const otherPreset = store.models["pos.preset"].get(2);
    store.models["product.combo"].get(1).qty_free = 2;
    const comboProduct1 = store.models["product.combo.item"].get(1);
    const comboProductExtra = store.models["product.combo.item"].get(2);
    const comboProduct2 = store.models["product.combo.item"].get(3);
    const template = store.models["product.template"].get(7);
    const order = store.addNewOrder();
    const order2 = store.addNewOrder();
    const order3 = store.addNewOrder();
    const order4 = store.addNewOrder();

    // Normal flow with extras
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboProduct1, qty: 2 }],
                [{ combo_item_id: comboProduct2, qty: 2 }],
            ],
            qty: 1,
        },
        order
    );

    let total = order.amount_total;
    order.setPreset(otherPreset);
    order.recomputeOrderData();
    expect(order.amount_total).toBe(total);

    // Normal flow
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [[{ combo_item_id: comboProduct1, qty: 2 }]],
            qty: 1,
        },
        order2
    );
    total = order2.amount_total;
    order2.setPreset(otherPreset);
    order2.recomputeOrderData();
    expect(order2.amount_total).toBe(total);

    // Flow with products with extra price
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboProduct1, qty: 2 }],
                [{ combo_item_id: comboProductExtra, qty: 2 }],
            ],
            qty: 1,
        },
        order3
    );
    total = order3.amount_total;
    order3.setPreset(otherPreset);
    order3.recomputeOrderData();
    expect(order3.amount_total).toBe(total);

    // Flow with all the same product
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboProduct1, qty: 2 }],
                [{ combo_item_id: comboProduct1, qty: 2 }],
            ],
            qty: 1,
        },
        order4
    );
    total = order4.amount_total;
    order4.setPreset(otherPreset);
    order4.recomputeOrderData();
    expect(order4.amount_total).toBe(total);
});
