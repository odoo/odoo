import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("uiState", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    expect(order.uiState).toEqual({
        unmerge: {},
        lastPrints: [],
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
    expect(result.data.payment_method_id.id).toBe(cashPaymentMethod.id);
    expect(result.data.amount).toBe(17.85);
});

test("getTotalDiscount", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const discount = order.getTotalDiscount();
    expect(discount).toBe(0);
    const taxTotals = order.prices.taxDetails;
    expect(taxTotals.base_amount).toBe(15);
    expect(taxTotals.total_amount).toBe(17.85);
    expect(taxTotals.tax_amount_currency).toBe(2.85);

    //Compute total of discount on the order
    const line1 = order.lines[0];
    const line2 = order.lines[1];
    line1.setDiscount(20);
    line2.setDiscount(50);

    expect(order.getTotalDiscount()).toBe(5.82);
    const taxTotalsWDiscount = order.prices.taxDetails;
    expect(taxTotalsWDiscount.base_amount).toBe(10.2);
    expect(taxTotalsWDiscount.total_amount).toBe(12.03);
    expect(taxTotalsWDiscount.tax_amount_currency).toBe(1.83);
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

test("isCustomerRequired", async () => {
    const posStore = await setupPosEnv();
    const order = await getFilledOrder(posStore);
    const existingPartner = posStore.models["res.partner"].get(3);

    expect(order.isCustomerRequired).toBe(false);
    {
        // preset - name identification
        const namePreset = posStore.models["pos.preset"].get(3);
        order.preset_id = namePreset;
        expect(order.isCustomerRequired).toBe(true);
        // with floating order name
        order.floating_order_name = "TEST-P";
        expect(order.isCustomerRequired).toBe(false);
        order.floating_order_name = "";
        // with assigned partner
        order.partner_id = existingPartner;
        expect(order.isCustomerRequired).toBe(false);
        order.partner_id = false;
    }
    {
        // preset - address identification
        const addressPreset = posStore.models["pos.preset"].get(4);
        order.preset_id = addressPreset;
        expect(order.isCustomerRequired).toBe(true);
        // with assigned partner
        order.partner_id = existingPartner;
        expect(order.isCustomerRequired).toBe(false);
        order.partner_id = false;
    }
    {
        // order invoicing
        order.preset_id = false;
        order.to_invoice = true;
        expect(order.isCustomerRequired).toBe(true);
        order.to_invoice = false;
    }
    {
        // split payment (customer account)
        const customerAccountMethod = posStore.models["pos.payment.method"].get(3);
        order.addPaymentline(customerAccountMethod);
        expect(order.isCustomerRequired).toBe(true);
        order.partner_id = existingPartner;
        expect(order.isCustomerRequired).toBe(false);
        order.partner_id = false;
        order.removePaymentline(order.payment_ids[0]);
    }
    expect(order.isCustomerRequired).toBe(false);
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

test("[get prices] check prices and taxes", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const data = order.prices;

    // Check taxes on order base_amount is 15 with 15% taxes
    const orderTaxes = data.taxDetails;
    expect(orderTaxes.base_amount).toBe(15.0);
    expect(orderTaxes.total_amount).toBe(17.85);
    expect(orderTaxes.tax_amount).toBe(2.85);

    // Order prices data also return the prices of all lines
    // Check first line with a price_unit of 3 and 3 qty
    const line1Data = data.baseLineByLineUuids[order.lines[0].uuid].tax_details;
    expect(line1Data.total_excluded).toBe(9.0);
    expect(line1Data.total_included).toBe(10.35);
    expect(line1Data.taxes_data[0].tax_amount).toBe(1.35);

    // Check second line with a price_unit of 3 and 2 qty
    const line2Data = data.baseLineByLineUuids[order.lines[1].uuid].tax_details;
    expect(line2Data.total_excluded).toBe(6.0);
    expect(line2Data.total_included).toBe(7.5);
    expect(line2Data.taxes_data[0].tax_amount).toBe(1.5);

    // Check with a discount on first line of 30%
    order.lines[0].setDiscount(30);
    const dataWDiscount = order.prices;
    const orderTaxesWDiscount = dataWDiscount.taxDetails;
    expect(orderTaxesWDiscount.base_amount).toBe(12.3);
    expect(orderTaxesWDiscount.total_amount).toBe(14.75);
    expect(orderTaxesWDiscount.tax_amount).toBe(2.45);

    // Check first line with a price_unit of 3, 3 qty and 30% discount
    const line1DataWDiscount = dataWDiscount.baseLineByLineUuids[order.lines[0].uuid].tax_details;
    expect(line1DataWDiscount.total_excluded).toBe(6.3);
    expect(line1DataWDiscount.total_included).toBe(7.25);
    expect(line1DataWDiscount.taxes_data[0].tax_amount).toBe(0.95);
    expect(line1DataWDiscount.discount_amount).toBe(3.1);

    // No discount values should still represent the line without discount
    expect(line1DataWDiscount.no_discount_total_excluded).toBe(9.0);
    expect(line1DataWDiscount.no_discount_total_included).toBe(10.35);
    expect(line1DataWDiscount.no_discount_taxes_data[0].tax_amount).toBe(1.35);
});
