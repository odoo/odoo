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
            last_general_customer_note: "",
            last_internal_note: "",
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
        const firstLine = order.lines[0];
        firstLine.setNote("Internal line note");
        firstLine.setCustomerNote("Customer line note");
        order.updateLastOrderChange();
        expect(order.uiState.last_general_customer_note).toBe("Customer note");
        expect(order.uiState.last_internal_note).toBe("Internal note");
        expect(firstLine.uiState.last_internal_note).toBe("Internal line note");
        expect(firstLine.uiState.last_customer_note).toBe("Customer line note");

        const originalQty = firstLine.getQuantity();
        firstLine.setQuantity(originalQty + 2);

        order.updateLastOrderChange();

        expect(order.prep_order_ids.length).toBe(2);
        const prepLines = store.models["pos.prep.line"].filter(
            (pl) => pl.pos_order_line_uuid === firstLine.uuid
        );
        const totalPrepQty = prepLines.reduce((sum, l) => sum + l.quantity - l.cancelled, 0);
        expect(totalPrepQty).toBe(originalQty + 2);

        expect(order.hasChange).toBe(false);
        expect(firstLine.uiState.savedQuantity).toBe(originalQty + 2);

        firstLine.setQuantity(1);

        order.updateLastOrderChange();
        expect(order.prep_order_ids.length).toBe(2);
        const totalPrepQtyAfterCancelled = prepLines.reduce(
            (sum, l) => sum + l.quantity - l.cancelled,
            0
        );
        expect(totalPrepQtyAfterCancelled).toBe(1);
        expect(prepLines[0].cancelled).toBe(originalQty - 1);
        expect(prepLines[1].cancelled).toBe(2);

        order.updateLastOrderChange({ cancelled: true });
        expect(prepLines[0].cancelled).toBe(originalQty);
        expect(prepLines[1].cancelled).toBe(2);
    });

    test("orderChanges", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);

        order.setGeneralCustomerNote("Customer note");
        order.setInternalNote("Internal note");
        const firstLine = order.lines[0];
        const secondLine = order.lines[1];

        const firstLineOriginalQty = firstLine.getQuantity();
        const secondLineOriginalQty = secondLine.getQuantity();

        //Check order notes and return
        const changes = order.orderChanges;
        expect(changes.general_customer_note).toBe("Customer note");
        expect(changes.internal_note).toBe("Internal note");
        expect(changes.nbrOfChanges).toBe(firstLineOriginalQty + secondLineOriginalQty);
        expect(Object.keys(changes.orderlines)).toEqual([firstLine.uuid, secondLine.uuid]);
        const firstOrderlineChange = changes.orderlines[firstLine.uuid];
        expect(firstOrderlineChange).toEqual({
            uuid: firstLine.uuid,
            basic_name: firstLine.getProduct().name,
            isCombo: firstLine.combo_item_id?.id,
            product_id: firstLine.getProduct().id,
            attribute_value_names: firstLine.attribute_value_ids.map((a) => a.name),
            quantity: firstLineOriginalQty,
            note: firstLine.getNote(),
            customer_note: firstLine.getCustomerNote(),
            pos_categ_id: firstLine.getProduct().pos_categ_ids[0]?.id ?? 0,
            pos_categ_sequence: firstLine.getProduct().pos_categ_ids[0]?.sequence ?? 0,
            group: firstLine.getCourse(),
        });

        //Check note update and change line quantity
        order.updateLastOrderChange();
        secondLine.setQuantity(secondLineOriginalQty + 2);
        firstLine.setNote("Internal line note");
        firstLine.setCustomerNote("Customer line note");
        const secondChanges = order.orderChanges;
        const noteUpdate = secondChanges.noteUpdate[firstLine.uuid];
        expect(noteUpdate.customer_note).toBe("Customer line note");
        expect(noteUpdate.note).toBe("Internal line note");
        expect(Object.keys(secondChanges.orderlines)).toEqual([secondLine.uuid]);
        const secondOrderlineChange = secondChanges.orderlines[secondLine.uuid];
        expect(secondOrderlineChange).toEqual({
            uuid: secondLine.uuid,
            basic_name: secondLine.getProduct().name,
            isCombo: secondLine.combo_item_id?.id,
            product_id: secondLine.getProduct().id,
            attribute_value_names: secondLine.attribute_value_ids.map((a) => a.name),
            quantity: 2,
            note: secondLine.getNote(),
            customer_note: secondLine.getCustomerNote(),
            pos_categ_id: secondLine.getProduct().pos_categ_ids[0]?.id ?? 0,
            pos_categ_sequence: secondLine.getProduct().pos_categ_ids[0]?.sequence ?? 0,
            group: secondLine.getCourse(),
        });

        //Check line delete
        order.updateLastOrderChange();
        const firstLineUuid = firstLine.uuid;
        const firstLineProduct = firstLine.getProduct();
        const firstLineIsCombo = firstLine.combo_item_id?.id;
        const firstLineAttributes = firstLine.attribute_value_ids.map((a) => a.name);
        order.removeOrderline(firstLine);
        const deleteLineChanges = order.orderChanges;
        expect(deleteLineChanges.nbrOfChanges).toBe(firstLineOriginalQty);
        const deleteOrderlineChange = deleteLineChanges.orderlines[firstLine.uuid];
        expect(deleteOrderlineChange).toEqual({
            uuid: firstLineUuid,
            basic_name: firstLineProduct.name,
            isCombo: firstLineIsCombo,
            product_id: firstLineProduct.id,
            attribute_value_names: firstLineAttributes,
            quantity: -firstLineOriginalQty,
            group: false,
        });
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
});
