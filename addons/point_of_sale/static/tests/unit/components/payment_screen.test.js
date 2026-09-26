import { test, expect, animationFrame, queryAll } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { localization } from "@web/core/l10n/localization";

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
    order.payment_ids[0].setAmount(1000);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -405.00");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -405.00");
});

test("addTip startingValue uses locale decimal separator on overpayment", async () => {
    const store = await setupPosEnv();
    store.config.iface_tipproduct = true;
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    const order = await getFilledOrder(store);
    const cashPm = store.models["pos.payment.method"].get(1);
    const { data: paymentLine } = order.addPaymentline(cashPm);
    paymentLine.setAmount(1000);
    expect(Math.abs(order.change)).toBe(405);

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
    expect(tipAmount).toBe(405);
});

test("payment methods: select a payment currency", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].get(1);
    const euro = store.models["res.currency"].get(125);

    paymentMethod.currency_ids = [euro];

    await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    const currencyButtons = queryAll(".paymentmethod button");
    expect(currencyButtons).toHaveLength(2);
    expect(currencyButtons[0].querySelector(".text-start")).toHaveText("USD");
    expect(currencyButtons[1].querySelector(".text-start")).toHaveText("EUR");

    await currencyButtons[1].click();
    await animationFrame();

    expect(order.payment_ids).toHaveLength(1);
    expect(order.payment_ids[0].payment_method_id).toBe(paymentMethod);
    expect(order.payment_ids[0].currency).toBe(euro);
    expect(currencyButtons[1]).toHaveClass("border-primary");
});
