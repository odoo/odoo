import { test, expect, describe, beforeEach, animationFrame } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { createPaymentLine } from "@point_of_sale/../tests/unit/utils";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import { MockServer, onRpc } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

definePosSelfModels();

beforeEach(async () => {
    const mockCreateBancontactPayment = async (request) => {
        const { params } = await request.json();
        const { payment_method_id, line_uuid, order_uuid } = params;

        // Should normally use the `access_token` from params
        // But we override `odoo.access_token` in `setupPosEnvForSelfOrder`
        const access_token = "test_access_token";
        const config = MockServer.env["pos.config"].find((c) => c.access_token == access_token);
        const order = MockServer.env["pos.order"].find((o) => o.uuid === order_uuid);
        const paymentMethod = MockServer.env["pos.payment.method"].browse(payment_method_id)[0];

        if (
            !config ||
            !order ||
            !paymentMethod ||
            paymentMethod.payment_provider !== "bancontact_pay" ||
            paymentMethod.config_ids.every((id) => id !== config.id)
        ) {
            throw new Error("Payment method not found");
        }

        return MockServer.env["pos.payment.method"].create_bancontact_payment(payment_method_id, {
            uuid: line_uuid,
            configId: config.id,
            amount: -window.__test_error__ || order.amount_total,
            currency: order.currency_id.name,
            description: "Test Bancontact Payment",
        });
    };

    onRpc("/pos-self-order/create-bancontact-pay-payment", mockCreateBancontactPayment);
});

describe("sendPaymentRequest", () => {
    test("failed to create bancontact payment", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const opts = { payment_status: "waiting" };
        const paymentline = createPaymentLine(store, order, display, opts);

        // Force the creation of the pos service for the test. The file
        // point_of_sale/static/src/app/components/popups/confirmation_dialog/confirmation_dialog.js
        // calls this service. In production, this file is not loaded for self-order,
        // so the pos service is never started and no error occurs.
        registry.category("services").add("pos", {
            start() {
                return {};
            },
        });

        let failed = false;
        try {
            window.__test_error__ = 400;
            await paymentline.payment_interface.sendPaymentRequest(paymentline);
        } catch {
            failed = true;
        }
        delete window.__test_error__;

        expect(failed).toBe(true);
        expect(paymentline.bancontact_id).toBeEmpty();
        expect(paymentline.qr_code).toBeEmpty();
        expect(paymentline.payment_status).toBe("waiting");

        await animationFrame();
        await waitFor(".o_alert_dialog");
        expect(".o_alert_dialog .modal-body").toHaveText("Failed to create payment (ERR: 400)");
    });

    test("success to create bancontact payment", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const display = store.models["pos.payment.method"].get(4);

        const opts = { payment_status: "waiting" };
        const paymentline = createPaymentLine(store, order, display, opts);

        const result = await paymentline.payment_interface.sendPaymentRequest(paymentline);

        expect(result).toBe(true);
        expect(paymentline.bancontact_id).toBe("bancontact_id");
        expect(paymentline.qr_code).toBe("bancontact_qr_code");
        expect(paymentline.payment_status).toBe("waiting");
    });
});
