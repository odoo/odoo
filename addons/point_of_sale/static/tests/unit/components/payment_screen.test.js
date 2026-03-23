import { test, expect, animationFrame } from "@odoo/hoot";
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
    order.payment_ids[0].setAmount(20);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -2.15");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -2.15");
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
