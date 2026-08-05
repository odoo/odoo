import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

// Preset 1 ("In") is the config default and carries fiscal position 1, mapped here to
// turn the 15% tax into the 25% one. Preset 2 ("Out") has no fiscal position.
const setupPresetFiscalPositions = (store) => {
    const mappedFp = store.models["account.fiscal.position"].get(1);
    mappedFp.update({ tax_map: { 1: [2] } });
    return {
        presetWithFp: store.models["pos.preset"].get(1),
        presetWithoutFp: store.models["pos.preset"].get(2),
        mappedFp,
    };
};

const getPaidOrder = async (store, { preset, fiscalPosition }) => {
    const order = store.addNewOrder({ preset_id: preset });
    order.fiscal_position_id = fiscalPosition;
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 2 },
        order
    );
    order.state = "paid";
    return order;
};

const refundOrder = async (comp, order) => {
    comp.setSelectedOrder(order);
    for (const line of order.lines) {
        comp.getToRefundDetail(line).qty = line.qty;
    }
    await comp.onDoRefund();
    return comp.pos.getOrder();
};

const appliedTaxIds = (line) =>
    line.prepareBaseLineForTaxesComputationExtraValues().tax_ids.map((tax) => tax.id);

test("refund keeps the fiscal position of the refunded order, not the default preset one", async () => {
    const store = await setupPosEnv();
    const { presetWithFp, presetWithoutFp, mappedFp } = setupPresetFiscalPositions(store);
    expect(store.config.default_preset_id.id).toBe(presetWithFp.id);

    const order = await getPaidOrder(store, { preset: presetWithoutFp, fiscalPosition: false });
    expect(order.priceIncl).toBe(230);

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    const refund = await refundOrder(comp, order);

    expect(refund.is_refund).toBe(true);
    expect(refund.fiscal_position_id?.id).toBe(undefined, {
        message: "the refund must not inherit the fiscal position of the default preset",
    });
    expect(appliedTaxIds(refund.lines[0])).toEqual([1]);
    expect(refund.priceIncl).toBe(-230);
    expect(mappedFp.tax_map[1]).toEqual([2]);
    // Sent explicitly, otherwise _complete_values_from_session falls back to the config default.
    expect(store.models.serializeForORM(refund).fiscal_position_id).toBe(false);
});

test("refund keeps the fiscal position of the refunded order when the default preset has none", async () => {
    const store = await setupPosEnv();
    const { presetWithFp, presetWithoutFp, mappedFp } = setupPresetFiscalPositions(store);
    store.config.default_preset_id = presetWithoutFp;

    const order = await getPaidOrder(store, { preset: presetWithFp, fiscalPosition: mappedFp });
    expect(order.priceIncl).toBe(250);

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    const refund = await refundOrder(comp, order);

    expect(refund.fiscal_position_id?.id).toBe(mappedFp.id);
    expect(appliedTaxIds(refund.lines[0])).toEqual([2]);
    expect(refund.priceIncl).toBe(-250);
});
