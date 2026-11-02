import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    createPaymentLine,
    getFilledOrder,
    mountPosDialog,
    setupPosEnv,
} from "@point_of_sale/../tests/unit/utils";

definePosModels();

async function mountQrPopup(paid, { verification } = {}) {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].get(1);
    const payment = createPaymentLine(store, order, paymentMethod, {
        amount: 25,
        qr_code: "data:image/png;base64,qr",
    });
    const calls = [];
    onRpc("pos.payment.method", "l10n_ph_qrph_verify_payment_status", ({ args }) => {
        calls.push(args);
        return verification ? verification.promise.then(() => paid) : paid;
    });
    const confirmed = [];
    await mountPosDialog(QRPopup, {
        ...payment.getQrPopupProps(),
        confirm: () => confirmed.push(true),
        close: () => {},
    });
    return { order, payment, paymentMethod, calls, confirmed };
}

test("confirming the QR popup asks the server about the order, its company and the amount", async () => {
    const { order, paymentMethod, calls, confirmed } = await mountQrPopup(true);

    await contains(".confirm-button").click();

    expect(calls).toEqual([[[paymentMethod.id], order.uuid, order.company.id, 25]]);
    expect(confirmed).toEqual([true]);
});

test("the QR popup does not confirm a payment that Maya has not received", async () => {
    const { calls, confirmed } = await mountQrPopup(false);

    await contains(".confirm-button").click();
    await animationFrame();

    expect(calls).toHaveLength(1);
    expect(confirmed).toEqual([]);
    expect(".modal:contains('Payment not received')").toHaveCount(1);
});

test("the QR popup cannot be confirmed again while Maya is being asked", async () => {
    const verification = Promise.withResolvers();
    const { calls, confirmed } = await mountQrPopup(true, { verification });

    await contains(".confirm-button").click();
    expect(".confirm-button").toHaveAttribute("disabled");
    expect(calls).toHaveLength(1);
    expect(confirmed).toEqual([]);

    verification.resolve();
    await animationFrame();
    expect(confirmed).toEqual([true]);
    expect(calls).toHaveLength(1);
});
