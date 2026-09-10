import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { localization } from "@web/core/l10n/localization";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

definePosModels();

test("Change always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const firstPm = store.models["pos.payment.method"].getFirst();
    order.config.iface_tax_included = "total";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(firstPm);
    order.payment_ids[0].setAmount(20);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -2.15");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -2.15");
});

test("showPaymentMethod", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    // Cashier Minimal
    store.cashier._role = "minimal";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(false);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Cashier Admin
    store.cashier._role = "admin";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(true);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + no payment interface
    order.is_refund = true;
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + payment interface not supporting refunds
    card.payment_interface = { supports_refunds: false };
    expect(comp.showPaymentMethod(card)).toBe(false);

    // Is Refund + payment interface supporting refunds
    card.payment_interface = { supports_refunds: true };
    expect(comp.showPaymentMethod(card)).toBe(true);
});

test("addTip startingValue uses locale decimal separator on overpayment", async () => {
    const store = await setupPosEnv();
    store.config.iface_tipproduct = true;
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    const order = await getFilledOrder(store);
    const cashPm = store.models["pos.payment.method"].get(1);
    const { data: paymentLine } = order.addPaymentline(cashPm);
    paymentLine.setAmount(22);
    expect(Math.abs(order.change)).toBe(4.15);

    let capturedStartingValue;
    const screen = {
        pos: store,
        currentOrder: order,
        env: { services: { localization } },
        dialog: {
            add: (_, props) => {
                capturedStartingValue = props.startingValue;
            },
        },
    };
    await PaymentScreen.prototype.addTip.call(screen);

    const tipAmount = PaymentScreen.prototype.computeNewTip.call(screen, {
        value: capturedStartingValue,
        type: "fixed",
    });
    expect(tipAmount).toBe(4.15);
});

test("Caba pay later always invoice", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const existingPartner = store.models["res.partner"].get(3);
    order.partner_id = existingPartner;
    const customerAccount = store.models["pos.payment.method"].get(3);
    const tax = store.models["account.tax"].get(1);
    tax.update({ tax_exigibility: "on_payment" });
    order.config.iface_tax_included = "total";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(order.isToInvoice()).toBe(false);
    await comp.addNewPaymentLine(customerAccount);
    expect(order.isToInvoice()).toBe(true);

    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    comp.toggleIsToInvoice();
    expect(order.isToInvoice()).toBe(false);
    const res = await validation.isOrderValid();
    expect(res).toBe(false);

    const validation2 = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    comp.toggleIsToInvoice();
    expect(order.isToInvoice()).toBe(true);
    const res2 = await validation2.isOrderValid();
    expect(res2).toBe(true);
});
