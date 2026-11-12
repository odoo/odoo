import { describe, advanceTime, expect, test, waitUntil } from "@odoo/hoot";
import { PaymentMethod } from "@pos_payment_method/payment_method";
import {
    defineModels,
    MockServer,
    models,
    runTestScope,
} from "../../../web/static/tests/web_test_helpers";
import { defineBusModels, waitForChannels } from "../../../bus/static/tests/bus_test_helpers";

describe.current.tags("headless");

class PosElectronicPayment extends models.ServerModel {
    _name = "pos.electronic.payment";

    start_payment(id, amount, currencyId, extraArgs) {
        if (amount < 0) {
            return { error: "Negative amount" };
        }
        return {
            transaction_id: "abc",
            status: extraArgs?.testReturnStatus ?? "pending",
        };
    }

    get_transaction_status(id, transaction_id) {
        return { transaction_id, status: "paid" };
    }
}

defineModels([PosElectronicPayment]);
defineBusModels();

class TestPaymentMethod extends PaymentMethod {
    pollingIntervalMs() {
        return 1000;
    }
}

class TestPaymentMethodNoPolling extends PaymentMethod {
    pollingIntervalMs() {
        return 0;
    }
}

test("starts payment", async () => {
    const paymentMethod = await runTestScope(() => new TestPaymentMethod(1));

    const response = await paymentMethod.startPayment(5.0, 1, {}, () => {});

    expect(response).toEqual({ transaction_id: "abc", status: "pending" });
});

test("throws if there is an error", async () => {
    const paymentMethod = await runTestScope(() => new TestPaymentMethod(1));

    const response = paymentMethod.startPayment(-5.0, 1, {}, () => {});

    await expect(response).rejects.toBeInstanceOf(Error);
});

test("starts polling payment status", async () => {
    const paymentMethod = await runTestScope(() => new TestPaymentMethod(1));
    let result = null;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => {
        result = response;
    });
    await advanceTime(1000);

    expect(result).toEqual({ transaction_id: "abc", status: "paid" });
});

test("listens on bus for payment status", async () => {
    const paymentMethod = await runTestScope(() => new TestPaymentMethodNoPolling(1));
    let result = null;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => {
        result = response;
    });
    await waitForChannels(["pos.electronic.payment:1"]);
    MockServer.env["bus.bus"]._sendone("pos.electronic.payment:1", "pos.electronic.payment", {
        transaction_id: "abc",
        status: "paid",
    });
    await waitUntil(() => !!result);

    expect(result).toEqual({ transaction_id: "abc", status: "paid" });
});

test("does not poll/listen if backend returns 'paid' status immediately", async () => {
    const paymentMethod = await runTestScope(() => new TestPaymentMethod(1));
    let callbackResponse = null;

    const startPaymentResponse = await paymentMethod.startPayment(
        5.0,
        1,
        { testReturnStatus: "paid" },
        (response) => {
            callbackResponse = response;
        }
    );

    expect(startPaymentResponse).toEqual({
        transaction_id: "abc",
        status: "paid",
    });
    expect(callbackResponse).toEqual({ transaction_id: "abc", status: "paid" });
});
