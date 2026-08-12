import { test, expect, waitFor, waitForNone } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { barcodeService } from "@barcodes/barcode_service";
import { setupPosEnv, getFilledOrder } from "../utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "../ui_utils";

definePosModels();

test("_onUpdateSelectedOrderline: refund moves to next", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const comboLine = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(7),
        payload: [
            [
                { combo_item_id: store.models["product.combo.item"].get(1), qty: 1 },
                { combo_item_id: store.models["product.combo.item"].get(3), qty: 1 },
            ],
            [],
        ],
        configure: false,
    });
    const line2Refund = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    // refund `line2Refund`
    const refundedOrder = store.createNewOrder();
    const refundingLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(8), qty: -2 },
        refundedOrder
    );
    line2Refund.refund_orderline_ids = [refundingLine.id];
    refundedOrder.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    await Utils.selectTicketFilter("Paid");
    await waitFor(".info-column");
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(comboLine.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "2" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "3" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});

test("Clicking Edit Payment closes OrderDetailsDialog and navigates to PaymentScreen", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store, {}, true);

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen._onInfoOrder(order);
    await waitFor(".o_dialog");
    await click(".fa-pencil");
    await waitForNone(".o_dialog");
    expect(order.getScreenData().name).toBe("PaymentScreen");
});

test("refund order should not have preset_id", async () => {
    const store = await setupPosEnv();

    const normalOrder = store.createNewOrder();
    expect(Boolean(normalOrder.preset_id)).toBe(true);

    const refundOrder = store.createNewOrder({ is_refund: true });
    expect(refundOrder.preset_id).toBeEmpty();
});

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

test("scanning a barcode on the ticket screen does not feed the refund quantity", async () => {
    // The buffer only drops fast multi-key sequences outside of test mode.
    patchWithCleanup(session, { test_mode: false });

    const store = await setupPosEnv();
    const order = store.addNewOrder({});
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 10 },
        order
    );
    order.state = "paid";
    const line = order.lines[0];

    const comp = await mountWithCleanup(TicketScreen, { props: {} });
    comp.setSelectedOrder(order);
    comp.state.selectedOrderlineIds[order.id] = line.id;

    const dialogTitles = [];
    patchWithCleanup(comp.dialog, {
        add: (_component, props) => dialogTitles.push(props.title.toString()),
    });

    // A scanner types the barcode a few ms per character.
    for (const char of "5901234123457") {
        window.dispatchEvent(new KeyboardEvent("keyup", { key: char }));
        await advanceTime(10);
    }
    await advanceTime(barcodeService.maxTimeBetweenKeysInMs);

    expect(comp.getToRefundDetail(line).qty).toBe(0);
    expect(dialogTitles).toEqual([]);
});
