import { waitUntil, expect, test, beforeEach } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc, patchWithCleanup } from "../../../../web/static/tests/web_test_helpers";
import { PaymentMollie } from "@pos_mollie/payment_mollie";

definePosModels();

const fakeMollieId = "fakeMollieId";
let lastError = null;

beforeEach(() => {
    lastError = null;
    patchWithCleanup(PaymentMollie.prototype, {
        _showMollieError(error) {
            lastError = error;
        },
    });
});

const setupMollie = async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const paymentMethod = store.models["pos.payment.method"].find(
        (pm) => pm.use_payment_terminal === "mollie"
    );
    const mollie = paymentMethod.payment_terminal;
    const paymentLine = order.addPaymentline(paymentMethod).data;

    const mockMollieCreatePaymentWithStatus = (status) => {
        onRpc("pos.payment.method", "mollie_create_payment", ({ args }) => {
            expect(args[0]).toBe(paymentMethod.id);
            expect(args[1]).toBe(17.85);
            expect(args[2]).toBe(paymentLine.uuid);
            expect(args[3]).toBe(order.session_id.id);
            return { id: fakeMollieId, status, _links: {} };
        });
    };

    return { mollie, paymentLine, mockMollieCreatePaymentWithStatus };
};

test("successful payment", async () => {
    const { mollie, paymentLine, mockMollieCreatePaymentWithStatus } = await setupMollie();
    mockMollieCreatePaymentWithStatus("open");

    const result = mollie.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.transaction_id === fakeMollieId);
    mollie.handleMollieStatusResponse(paymentLine, {
        status: "paid",
        card_no: "1234",
        card_brand: "BRAND",
        card_type: "TYPE",
    });

    await expect(result).resolves.toBe(true);
    expect(lastError).toBe(null);
    expect(paymentLine.card_no).toBe("1234");
    expect(paymentLine.card_brand).toBe("BRAND");
    expect(paymentLine.card_type).toBe("TYPE");
});

test("shows error on invalid payment state", async () => {
    const { mollie, paymentLine, mockMollieCreatePaymentWithStatus } = await setupMollie();
    mockMollieCreatePaymentWithStatus("failed");

    const result = await mollie.sendPaymentRequest(paymentLine.uuid);

    expect(result).toBe(false);
    expect(lastError).toInclude("Failed to initiate payment");
});

test("shows error on failed payment", async () => {
    const { mollie, paymentLine, mockMollieCreatePaymentWithStatus } = await setupMollie();
    mockMollieCreatePaymentWithStatus("open");

    const result = mollie.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.transaction_id === fakeMollieId);
    mollie.handleMollieStatusResponse(paymentLine, {
        status: "failed",
        status_reason: { message: "Test Mollie Error" },
    });

    await expect(result).resolves.toBe(false);
    expect(lastError).toBe("Test Mollie Error");
});

test("shows error on expired payment", async () => {
    const { mollie, paymentLine, mockMollieCreatePaymentWithStatus } = await setupMollie();
    mockMollieCreatePaymentWithStatus("open");

    const result = mollie.sendPaymentRequest(paymentLine.uuid);
    await waitUntil(() => paymentLine.transaction_id === fakeMollieId);
    mollie.handleMollieStatusResponse(paymentLine, { status: "expired" });

    await expect(result).resolves.toBe(false);
    expect(lastError).toBe("The payment has timed out.");
});
