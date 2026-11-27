import { describe, afterEach, beforeEach, expect, test, waitUntil } from "@odoo/hoot";
import { defineModels, models, runTestScope } from "../../../web/static/tests/web_test_helpers";
import { defineBusModels } from "../../../bus/static/tests/bus_test_helpers";
import { PaymentMethodStripe } from "../src/payment_method_stripe";

describe.current.tags("headless");

class PosElectronicPayment extends models.ServerModel {
    _name = "pos.electronic.payment";

    start_payment(id, amount) {
        return {
            transaction_id: "test_stripe_transaction",
            status: "pending",
            terminal_serial_number: "TEST",
            client_secret: "SECRET",
            allow_tips: amount === 100,
        };
    }

    get_transaction_status(id, transaction_id) {
        if (transaction_id === "resumed_payment" && !FakeStripeSdk.calls.length) {
            return {
                transaction_id,
                status: "pending",
                stripe_status: "requires_payment_method",
                terminal_serial_number: "TEST",
                client_secret: "SECRET",
            };
        }
        return { transaction_id, status: "paid", card_type: "Visa" };
    }
}

defineModels([PosElectronicPayment]);
defineBusModels();

class FakeStripeSdk {
    static dummyReader = {
        serial_number: "TEST",
    };
    static dummyPayment = {
        id: "test_stripe_transaction",
    };

    constructor(callbacks) {
        this.callbacks = callbacks;
    }

    static reset() {
        this.instance = null;
        this.calls = [];
        this.waitForCollectCancel = false;
        this.waitForProcessCancel = false;
        this.forceError = false;
        this.dummyPayment.id = "test_stripe_transaction";
    }

    static get calledMethods() {
        return this.calls.map(([method]) => method);
    }

    static create(callbacks) {
        if (this.instance) {
            throw new Error("Tried to instantiate the Stripe SDK multiple times");
        }
        this.instance = new FakeStripeSdk(callbacks);
        return this.instance;
    }

    async discoverReaders() {
        FakeStripeSdk.calls.push(["discoverReaders"]);
        return { discoveredReaders: [FakeStripeSdk.dummyReader] };
    }

    async connectReader(reader, options) {
        FakeStripeSdk.calls.push(["connectReader", reader, options]);
        return reader;
    }

    async collectPaymentMethod(secret, options) {
        FakeStripeSdk.calls.push(["collectPaymentMethod", secret, options]);
        if (FakeStripeSdk.waitForCollectCancel) {
            this.collectPromise = Promise.withResolvers();
            await this.collectPromise.promise;
            return { error: { code: "cancel", message: "cancelled" } };
        }
        if (FakeStripeSdk.forceError) {
            return { error: { code: "ERROR", message: "Message" } };
        }
        return { paymentIntent: FakeStripeSdk.dummyPayment };
    }

    async cancelCollectPaymentMethod() {
        FakeStripeSdk.calls.push(["cancelCollectPaymentMethod"]);
        if (this.collectPromise) {
            this.collectPromise.resolve();
            this.collectPromise = null;
        }
        return {};
    }

    async processPayment(paymentIntent) {
        FakeStripeSdk.calls.push(["processPayment", paymentIntent]);
        if (FakeStripeSdk.waitForProcessCancel) {
            this.processPromise = Promise.withResolvers();
            await this.processPromise.promise;
            return { error: { code: "cancel", message: "cancelled" } };
        }
        return { paymentIntent };
    }

    async cancelProcessPayment() {
        FakeStripeSdk.calls.push(["cancelProcessPayment"]);
        if (this.processPromise) {
            this.processPromise.resolve();
            this.processPromise = null;
        }
        return {};
    }

    async disconnectReader() {
        FakeStripeSdk.calls.push(["disconnectReader"]);
    }
}

beforeEach(() => {
    window.StripeTerminal = FakeStripeSdk;
    FakeStripeSdk.reset();
});

afterEach(() => {
    delete window.StripeTerminal;
});

test("normal payment flow makes expected SDK calls", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;

    const response = await paymentMethod.startPayment(
        5.0,
        1,
        {},
        (response) => (paymentResult = response)
    );

    expect(response).toMatchObject({
        transaction_id: "test_stripe_transaction",
        status: "pending",
        terminal_serial_number: "TEST",
        client_secret: "SECRET",
    });
    expect(FakeStripeSdk.instance).not.toBe(null);

    await waitUntil(() => FakeStripeSdk.calls.length === 5);
    expect(FakeStripeSdk.calls[0]).toEqual(["discoverReaders"]);
    expect(FakeStripeSdk.calls[1]).toEqual([
        "connectReader",
        FakeStripeSdk.dummyReader,
        { fail_if_in_use: true },
    ]);
    expect(FakeStripeSdk.calls[2]).toEqual([
        "collectPaymentMethod",
        "SECRET",
        { config_override: { enable_customer_cancellation: true, skip_tipping: true } },
    ]);
    expect(FakeStripeSdk.calls[3]).toEqual(["processPayment", FakeStripeSdk.dummyPayment]);
    expect(FakeStripeSdk.calls[4]).toEqual(["disconnectReader"]);

    expect(paymentResult).toEqual({
        status: "paid",
        card_type: "Visa",
        transaction_id: "test_stripe_transaction",
    });
});

test("skip tipping is false if allow tips is true", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));

    await paymentMethod.startPayment(100, 1, {}, () => {});

    await waitUntil(() => FakeStripeSdk.calls.length >= 3);
    expect(FakeStripeSdk.calls[2]).toEqual([
        "collectPaymentMethod",
        "SECRET",
        { config_override: { enable_customer_cancellation: true, skip_tipping: false } },
    ]);
});

test("cancelling immediately after starting does not call collectPaymentMethod", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => (paymentResult = response));
    await paymentMethod.cancelTransaction("test_stripe_transaction");
    await waitUntil(() => paymentResult !== null);

    expect(FakeStripeSdk.calledMethods).not.toInclude("collectPaymentMethod");
    expect(paymentResult).toMatchObject({
        status: "failed",
        transaction_id: "test_stripe_transaction",
    });
});

test("cancelling during collection calls cancelCollectPaymentMethod", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;
    FakeStripeSdk.waitForCollectCancel = true;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => (paymentResult = response));
    await waitUntil(() => FakeStripeSdk.instance.collectPromise);
    await paymentMethod.cancelTransaction("test_stripe_transaction");
    await waitUntil(() => paymentResult !== null);

    expect(FakeStripeSdk.calledMethods).toInclude("collectPaymentMethod");
    expect(FakeStripeSdk.calledMethods).toInclude("cancelCollectPaymentMethod");
    expect(paymentResult).toMatchObject({
        status: "failed",
        transaction_id: "test_stripe_transaction",
    });
});

test("cancelling during processing calls cancelProcessPayment", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;
    FakeStripeSdk.waitForProcessCancel = true;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => (paymentResult = response));
    await waitUntil(() => FakeStripeSdk.instance.processPromise);
    await paymentMethod.cancelTransaction("test_stripe_transaction");
    await waitUntil(() => paymentResult !== null);

    expect(FakeStripeSdk.calledMethods).toInclude("processPayment");
    expect(FakeStripeSdk.calledMethods).toInclude("cancelProcessPayment");
    expect(paymentResult).toMatchObject({
        status: "failed",
        transaction_id: "test_stripe_transaction",
    });
});

test("resuming a payment that is finished returns immediately", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;

    paymentMethod.startListening(
        "test_stripe_transaction",
        (response) => (paymentResult = response)
    );
    await waitUntil(() => paymentResult !== null);

    expect(FakeStripeSdk.calledMethods).toHaveLength(0);
    expect(paymentResult).toMatchObject({
        status: "paid",
        transaction_id: "test_stripe_transaction",
    });
});

test("resuming a payment that is not processed resumes processing", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    FakeStripeSdk.dummyPayment.id = "resumed_payment";
    let paymentResult = null;

    paymentMethod.startListening("resumed_payment", (response) => (paymentResult = response));
    await waitUntil(() => paymentResult !== null);

    expect(FakeStripeSdk.calledMethods).toHaveLength(5);
    expect(paymentResult).toMatchObject({
        status: "paid",
        transaction_id: "resumed_payment",
    });
});

test("errors are handled and returned to the caller", async () => {
    const paymentMethod = await runTestScope(() => new PaymentMethodStripe(1));
    let paymentResult = null;
    FakeStripeSdk.forceError = true;

    await paymentMethod.startPayment(5.0, 1, {}, (response) => (paymentResult = response));
    await waitUntil(() => paymentResult !== null);

    expect(paymentResult).toMatchObject({
        status: "failed",
        transaction_id: "test_stripe_transaction",
        error: "Error received from Stripe: ERROR\n\nMessage",
    });
});
