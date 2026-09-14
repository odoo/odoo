import { expect, test } from "@odoo/hoot";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

import { definePosModels } from "../data/generate_model_definitions.js";
import { setupPosEnv } from "../utils.js";
import { getFilledOrderForPriceCheck, prepareRoundingVals } from "./utils.js";

definePosModels();

test("zero cash payment preserves explicit rounding intent through validation", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP");
    const order = await getFilledOrderForPriceCheck(store);
    order.addPaymentline(cardPm).data.setAmount(order.totalDue - 0.02);
    const cashPayment = order.addPaymentline(cashPm).data;
    cashPayment.setAmount(0);

    expect(order.orderIsRounded).toBe(true);
    expect(order.remainingDue).toBe(0);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    await validation.validateOrder(false);

    expect(order.state).toBe("paid");
    expect(order.payment_ids.map((payment) => payment.uuid)).toInclude(
        cashPayment.uuid,
    );
    expect(cashPayment.amount).toBe(0);
});

test("cash rounding can settle an entire small order at zero", async () => {
    const store = await setupPosEnv();
    const { cashPm } = prepareRoundingVals(store, 0.05, "HALF-UP");
    for (const [id, price] of [
        [15, 0.02],
        [16, 0],
    ]) {
        const product = store.models["product.template"].get(id);
        product.taxes_id = [];
        product.list_price = price;
        product.product_variant_ids[0].lst_price = price;
    }
    const order = await getFilledOrderForPriceCheck(store);
    const cashPayment = order.addPaymentline(cashPm).data;
    expect(order.priceIncl).toBe(0.02);
    expect(cashPayment.amount).toBe(0);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    await validation.validateOrder(false);

    expect(order.state).toBe("paid");
    expect(order.payment_ids.map((payment) => payment.uuid)).toInclude(
        cashPayment.uuid,
    );
    expect(order.amountPaid).toBe(0);
});

test("unrelated zero bank payment is removed during cash-rounded validation", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP");
    const order = await getFilledOrderForPriceCheck(store);
    const cashPayment = order.addPaymentline(cashPm).data;
    const bankPayment = order.addPaymentline(cardPm).data;
    bankPayment.setAmount(0);

    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    await validation.validateOrder(false);

    expect(order.state).toBe("paid");
    expect(order.payment_ids.map((payment) => payment.uuid)).toEqual([
        cashPayment.uuid,
    ]);
});

test("Rounding sale HALF-UP 0.05 (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.01);
    expect(order.change).toBe(0);
});

test("Rounding sale HALF-UP 0.05 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.01);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.01);
    expect(order.change).toBe(0);

    order.payment_ids[0].delete();
    order.addPaymentline(cashPm);
    order.payment_ids[0].setAmount(52.5);
    expect(order.payment_ids[0].amount).toBe(52.5);
    expect(order.appliedRounding).toBe(0);
    expect(order.remainingDue).toBe(0.05);
    expect(order.canBeValidated()).toBe(false);
});

test("Rounding sale UP 10  (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 10, "UP", true);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(7.46);
    expect(order.change).toBe(0);
});

test("Rounding sale UP 10 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 10, "UP", false);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(7.46);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(7.46);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(60);
    order.payment_ids[0].setAmount(70);
    expect(order.payment_ids[0].amount).toBe(70);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(-10);
});

test("Rounding sale DOWN 10 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 10, "DOWN", false);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(50);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-2.54);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(50);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-2.54);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(50);
    order.payment_ids[0].setAmount(70);
    expect(order.payment_ids[0].amount).toBe(70);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(-20);
});

test("Rounding sale DOWN 1 (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 1, "DOWN", true);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.54);
    expect(order.change).toBe(0);
});

test("Rounding sale DOWN 1 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 1, "DOWN", false);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.54);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.54);
    expect(order.change).toBe(0);
});

test("Rounding refund HALF-UP 0.05 (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.01);
    expect(order.change).toBe(0);
});

test("Rounding refund HALF-UP 0.05 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.01);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-52.55);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-0.01);
    expect(order.change).toBe(0);
});

test("Rounding refund UP 10 (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 10, "UP", true);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-7.46);
    expect(order.change).toBe(0);
});

test("Rounding refund UP 10 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 10, "UP", false);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-7.46);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-60);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(-7.46);
    expect(order.change).toBe(0);
});

test("Rounding refund DOWN 1 (cash only)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 1, "DOWN", true);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-52.54);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.54);
    expect(order.change).toBe(0);
});

test("Rounding refund DOWN 1 (all methods)", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 1, "DOWN", false);
    const order = await getFilledOrderForPriceCheck(store);

    order.is_refund = true;
    order.lines.map((line) => line.setQuantity(-line.qty));

    expect(order.displayPrice).toBe(-52.54);

    order.addPaymentline(cardPm);
    expect(order.payment_ids[0].amount).toBe(-52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.54);
    expect(order.change).toBe(0);
    order.payment_ids[0].delete();
    expect(order.canBeValidated()).toBe(false);

    order.addPaymentline(cashPm);
    expect(order.payment_ids[0].amount).toBe(-52);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.54);
    expect(order.change).toBe(0);
});

test("Rouding sale HALF-UP 0.05 with two payment method", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const order = await getFilledOrderForPriceCheck(store);

    expect(order.displayPrice).toBe(52.54);

    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(2.54);
    expect(order.payment_ids[0].amount).toBe(2.54);
    expect(order.canBeValidated()).toBe(false);
    expect(order.remainingDue).toBe(50.01);
    order.addPaymentline(cashPm);

    expect(order.payment_ids[1].amount).toBe(50.01);
    expect(order.remainingDue).toBe(0);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0.01);
    expect(order.change).toBe(0);

    order.config_id.only_round_cash_method = true;
    order.payment_ids = [];
    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(2.54);
    expect(order.payment_ids[0].amount).toBe(2.54);
    expect(order.canBeValidated()).toBe(false);
    expect(order.remainingDue).toBe(50);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
    order.addPaymentline(cashPm);
    expect(order.payment_ids[1].amount).toBe(50);
    expect(order.remainingDue).toBe(0);
    expect(order.canBeValidated()).toBe(true);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(0);
});
