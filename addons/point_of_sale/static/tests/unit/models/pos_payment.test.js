import { Deferred, expect, freezeTime, mockDate, test } from "@odoo/hoot";
import { definePosModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import {
    PaymentInterfaceV2,
    REQUEST_DROPPED,
} from "@point_of_sale/app/utils/payment/payment_interface_v2";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "../utils";

const { DateTime } = luxon;

definePosModels();

test("uiState", async () => {
    mockDate("2025-01-09 12:00:00");
    freezeTime();

    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    expect(paymentline.uiState).toEqual({
        initStateDate: DateTime.fromISO("2025-01-09T13:00:00"),
    });
});

test("isDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // done
    paymentline.payment_status = "done";
    expect(paymentline.isDone()).toBe(true);

    // pending
    paymentline.payment_status = "pending";
    expect(paymentline.isDone()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isDone()).toBe(true);
});

test("isProcessing", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    const processingStatuses = [
        "waiting",
        "waiting_cancel",
        "waiting_card",
        "waiting_scan",
        "waiting_capture",
        "force_done",
    ];

    for (const status of processingStatuses) {
        paymentline.payment_status = status;
        expect(paymentline.isProcessing()).toBe(true);
    }

    // non-processing status
    paymentline.payment_status = "done";
    expect(paymentline.isProcessing()).toBe(false);

    // no status
    paymentline.payment_status = null;
    expect(paymentline.isProcessing()).toBe(false);
});

test("isRefund", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // positive amount
    expect(paymentline.isRefund).toBe(false);

    // negative amount
    paymentline.amount = -10;
    expect(paymentline.isRefund).toBe(true);

    // zero amount
    paymentline.amount = 0;
    expect(paymentline.isRefund).toBe(false);
});

test("pay", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "pending" });

    // Successful
    card.payment_interface.sendPaymentRequest = async () => {
        expect(paymentline.payment_status).toBe("waiting");
        return true;
    };
    expect(await paymentline.pay()).toBe(true);
    expect(paymentline.payment_status).toBe("done");

    // Failed
    card.payment_interface.sendPaymentRequest = async () => false;
    expect(await paymentline.pay()).toBe(false);
    expect(paymentline.payment_status).toBe("retry");

    // Error
    card.payment_interface.sendPaymentRequest = async () => {
        throw new Error("Request failed");
    };
    await expect(paymentline.pay()).rejects.toThrow("Request failed");
    expect(paymentline.payment_status).toBe("retry");
});

test("cancelPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waiting_card";
    card.payment_interface.sendPaymentCancel = async () => {
        expect(paymentline.payment_status).toBe("waiting_cancel");
        return true;
    };
    expect(await paymentline.cancelPayment()).toBe(true);
    expect(paymentline.payment_status).toBe("retry");

    // Failed: back to the status before the cancel
    for (const status of ["waiting_card", "waiting_scan", "waiting"]) {
        paymentline.payment_status = status;
        card.payment_interface.sendPaymentCancel = async () => false;
        expect(await paymentline.cancelPayment()).toBe(false);
        expect(paymentline.payment_status).toBe(status);
    }

    // Error: back to the status before the cancel
    paymentline.payment_status = "waiting_scan";
    card.payment_interface.sendPaymentCancel = async () => {
        throw new Error("Cancel failed");
    };
    await expect(paymentline.cancelPayment()).rejects.toThrow("Cancel failed");
    expect(paymentline.payment_status).toBe("waiting_scan");
});

test("forceDone", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const data = { payment_status: "waiting" };
    const paymentline = createPaymentLine(store, order, card, data);

    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("done");
});

test("forceCancel", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterface(store, card);
    const data = { payment_status: "waiting" };
    const paymentline = createPaymentLine(store, order, card, data);

    paymentline.forceCancel();
    expect(paymentline.payment_status).toBe("retry");
});

test("canBeAdjusted", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface + is cash
    card.type = "cash";
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(false);

    // no payment interface + is not cash
    card.type = "bank";
    card.payment_method_type = "none";
    expect(paymentline.canBeAdjusted()).toBe(true);

    // payment interface: its hook decides, from the uuid of the line
    card.payment_interface = new PaymentInterface(store, card);
    expect(paymentline.canBeAdjusted()).toBe(false);
    card.payment_interface.canBeAdjusted = (uuid) => uuid === paymentline.uuid;
    expect(paymentline.canBeAdjusted()).toBe(true);
});

test("adjustAmount", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);

    // no payment interface: nothing to adjust
    card.payment_interface = null;
    expect(await paymentline.adjustAmount(20)).toBe(true);
    expect(paymentline.getAmount()).toBe(10);

    // accepted
    card.payment_interface = new PaymentInterface(store, card);
    card.payment_interface.sendPaymentAdjust = async (uuid) => {
        expect(uuid).toBe(paymentline.uuid);
        expect(paymentline.payment_status).toBe("waiting");
        expect(paymentline.getAmount()).toBe(30);
        return true;
    };
    expect(await paymentline.adjustAmount(20)).toBe(true);
    expect(paymentline.getAmount()).toBe(30);
    expect(paymentline.payment_status).toBe("done");

    // refused: the amount is restored
    card.payment_interface.sendPaymentAdjust = async () => false;
    expect(await paymentline.adjustAmount(5)).toBe(false);
    expect(paymentline.getAmount()).toBe(30);
    expect(paymentline.payment_status).toBe("done");

    // error: the amount is restored
    card.payment_interface.sendPaymentAdjust = async () => {
        throw new Error("Network error");
    };
    await expect(paymentline.adjustAmount(5)).rejects.toThrow("Network error");
    expect(paymentline.getAmount()).toBe(30);
    expect(paymentline.payment_status).toBe("done");
});

// ----- PaymentInterfaceV2 -----

test("pay, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterfaceV2(store, card);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "pending" });

    // Successful
    card.payment_interface.sendPaymentRequest = async () => {
        expect(paymentline.payment_status).toBe("waiting");
        return true;
    };
    expect(await paymentline.pay()).toBe(true);
    expect(paymentline.payment_status).toBe("done");

    // Failed
    card.payment_interface.sendPaymentRequest = async () => false;
    expect(await paymentline.pay()).toBe(false);
    expect(paymentline.payment_status).toBe("retry");

    // Error
    card.payment_interface.sendPaymentRequest = async () => {
        throw new Error("Request failed");
    };
    await expect(paymentline.pay()).rejects.toThrow("Request failed");
    expect(paymentline.payment_status).toBe("retry");

    // Forced while it was being sent: the force is kept, the answer is late
    const lateResponses = [];
    card.payment_interface.handleLateResponse = async (line, response) => {
        lateResponses.push(response);
    };
    for (const [force, status] of [
        ["forceDone", "done"],
        ["forceCancel", "retry"],
    ]) {
        card.payment_interface.sendPaymentRequest = async (line) => {
            line[force]();
            return true;
        };
        expect(await paymentline.pay()).toBe(false);
        expect(paymentline.payment_status).toBe(status);

        // Waiting for the answer does not overwrite the status
        card.payment_interface.sendPaymentRequest = async (line, request) => {
            line[force]();
            return request.wait("waiting_card");
        };
        expect(await paymentline.pay()).toBe(false);
        expect(paymentline.payment_status).toBe(status);

        // Neither does an error
        card.payment_interface.sendPaymentRequest = async (line) => {
            line[force]();
            throw new Error("Request failed");
        };
        await expect(paymentline.pay()).rejects.toThrow("Request failed");
        expect(paymentline.payment_status).toBe(status);
    }
    expect(lateResponses).toEqual([true, true]);
});

test("answerRequest", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentInterface = new PaymentInterfaceV2(store, card);
    card.payment_interface = paymentInterface;
    const paymentline = createPaymentLine(store, order, card);
    let handled = 0;
    let accepted = 0;
    let late = 0;
    let handling = Promise.resolve();
    paymentInterface.handlePaymentResponse = async (line, response) => {
        handled++;
        await handling;
        line.payment_status = response ? "done" : "retry";
        return response;
    };
    paymentInterface.handleLateResponse = async () => late++;
    store.onPaymentAccepted = () => accepted++;
    paymentInterface.sendPaymentRequest = async (line, request) => request.wait("waiting_card");

    // Answered twice while pay() waits: handled once
    let pay = paymentline.pay();
    expect(paymentline.payment_status).toBe("waiting_card");
    paymentInterface.answerRequest(paymentline, true);
    paymentInterface.answerRequest(paymentline, true);
    expect(await pay).toBe(true);
    expect(handled).toBe(1);

    // Answered twice after a reload: handled and accepted once
    handled = 0;
    paymentline.payment_status = "waiting_card";
    const restored = paymentInterface.restorePendingRequest(paymentline);
    paymentInterface.answerRequest(paymentline, true);
    paymentInterface.answerRequest(paymentline, true);
    await restored;
    expect(handled).toBe(1);
    expect(accepted).toBe(1);
    expect(paymentline.payment_status).toBe("done");

    // Forced or cancelled while the answer is handled: nothing happens
    handled = 0;
    handling = new Deferred();
    pay = paymentline.pay();
    paymentInterface.answerRequest(paymentline, true);
    paymentline.forceCancel();
    expect(await paymentline.cancelPayment()).toBe(false);
    handling.resolve();
    expect(await pay).toBe(true);
    expect(handled).toBe(1);
    expect(paymentline.payment_status).toBe("done");

    // Answered after a force: one late answer, the line is left as it is
    handled = 0;
    pay = paymentline.pay();
    paymentline.forceCancel();
    expect(await pay).toBe(false);
    paymentInterface.answerRequest(paymentline, true);
    paymentInterface.answerRequest(paymentline, true);
    expect(handled).toBe(0);
    expect(late).toBe(1);
    expect(paymentline.payment_status).toBe("retry");

    // The cashier applies the late answer: handled as if it came in time
    const request = paymentInterface.requests[paymentline.uuid];
    await paymentInterface.applyLateResponse(paymentline, true, request);
    expect(handled).toBe(1);
    expect(request.state).toBe("answered");
    expect(paymentline.payment_status).toBe("done");

    // Not once the line started another request
    paymentline.payment_status = "retry";
    paymentInterface.newRequest(paymentline);
    await paymentInterface.applyLateResponse(paymentline, true, request);
    expect(handled).toBe(1);
    expect(paymentline.payment_status).toBe("retry");
});

test("cancelPayment, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterfaceV2(store, card);
    const paymentline = createPaymentLine(store, order, card);

    // Successful
    paymentline.payment_status = "waiting_card";
    card.payment_interface.sendPaymentCancel = async () => {
        expect(paymentline.payment_status).toBe("waiting_cancel");
        return true;
    };
    expect(await paymentline.cancelPayment()).toBe(true);
    expect(paymentline.payment_status).toBe("retry");

    // Failed: back to the status before the cancel
    for (const status of ["waiting_card", "waiting_scan", "waiting"]) {
        paymentline.payment_status = status;
        card.payment_interface.sendPaymentCancel = async () => false;
        expect(await paymentline.cancelPayment()).toBe(false);
        expect(paymentline.payment_status).toBe(status);
    }

    // Error: back to the status before the cancel
    paymentline.payment_status = "waiting_scan";
    card.payment_interface.sendPaymentCancel = async () => {
        throw new Error("Cancel failed");
    };
    await expect(paymentline.cancelPayment()).rejects.toThrow("Cancel failed");
    expect(paymentline.payment_status).toBe("waiting_scan");

    // Payment answered during the cancel: its result is kept
    store.onPaymentAccepted = () => {};
    for (const isPaid of [true, false]) {
        for (const cancelResult of [true, false]) {
            paymentline.payment_status = "waiting_card";
            const restored = card.payment_interface.restorePendingRequest(paymentline);
            card.payment_interface.sendPaymentCancel = async () => {
                card.payment_interface.answerRequest(paymentline, isPaid);
                await restored;
                return cancelResult;
            };
            expect(await paymentline.cancelPayment()).toBe(false);
            expect(paymentline.payment_status).toBe(isPaid ? "done" : "retry");
        }
    }
    paymentline.payment_status = "waiting_card";
    const restored = card.payment_interface.restorePendingRequest(paymentline);
    card.payment_interface.sendPaymentCancel = async () => {
        card.payment_interface.answerRequest(paymentline, true);
        await restored;
        throw new Error("Cancel failed");
    };
    expect(await paymentline.cancelPayment()).toBe(false);
    expect(paymentline.payment_status).toBe("done");

    // Answer received but still being handled (status not set yet)
    paymentline.payment_status = "waiting_card";
    card.payment_interface.newRequest(paymentline);
    card.payment_interface.sendPaymentCancel = async () => {
        card.payment_interface.answerRequest(paymentline, true);
        return true;
    };
    expect(await paymentline.cancelPayment()).toBe(false);
    expect(paymentline.payment_status).toBe("waiting_cancel");

    // Already settled: nothing is sent
    card.payment_interface.sendPaymentCancel = async () => {
        throw new Error("Should not be sent");
    };
    expect(await paymentline.cancelPayment()).toBe(false);
    expect(paymentline.payment_status).toBe("waiting_cancel");
});

test("forceDone and forceCancel, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterfaceV2(store, card);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "waiting" });

    // A waiting pay() receives REQUEST_DROPPED
    for (const [force, status] of [
        ["forceDone", "done"],
        ["forceCancel", "retry"],
    ]) {
        const response = card.payment_interface.newRequest(paymentline).wait("waiting_card");
        paymentline[force]();
        expect(await response).toBe(REQUEST_DROPPED);
        expect(paymentline.payment_status).toBe(status);
    }

    // Already forced: a second force does nothing
    paymentline.forceDone();
    expect(paymentline.payment_status).toBe("retry");
});

test("late answers, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentInterface = new PaymentInterfaceV2(store, card);
    card.payment_interface = paymentInterface;
    const paymentline = createPaymentLine(store, order, card);
    let handled = 0;
    let accepted = 0;
    const errors = [];
    paymentInterface.handlePaymentResponse = async (line, response) => {
        handled++;
        line.payment_status = response ? "done" : "retry";
        return response;
    };
    paymentInterface.showError = (message) => errors.push(message);
    store.onPaymentAccepted = () => accepted++;
    paymentInterface.sendPaymentRequest = async (line, request) => request.wait("waiting_card");
    let late;
    const handleLateResponse = paymentInterface.handleLateResponse.bind(paymentInterface);
    paymentInterface.handleLateResponse = (...args) => (late = handleLateResponse(...args));

    // Paid after a force done: applied silently, the order is not validated
    let pay = paymentline.pay();
    paymentline.forceDone();
    expect(await pay).toBe(false);
    paymentInterface.answerRequest(paymentline, true);
    await late;
    expect(handled).toBe(1);
    expect(accepted).toBe(0);
    expect(paymentline.payment_status).toBe("done");
    expect(paymentInterface.requests[paymentline.uuid]).toBe(undefined);

    // Paid after the request was replaced: the line is left, the cashier is told
    handled = 0;
    pay = paymentline.pay();
    const replaced = paymentInterface.requests[paymentline.uuid];
    paymentline.forceCancel();
    expect(await pay).toBe(false);
    paymentInterface.newRequest(paymentline);
    replaced.answer(true);
    await late;
    expect(handled).toBe(0);
    expect(errors.length).toBe(1);
    expect(paymentline.payment_status).toBe("retry");

    // An answer no pay() waits for that fails to be handled: retry, rethrown
    paymentInterface.handlePaymentResponse = async () => {
        throw new Error("Handling failed");
    };
    paymentline.payment_status = "waiting_card";
    const restored = paymentInterface.restorePendingRequest(paymentline);
    paymentInterface.answerRequest(paymentline, true);
    await expect(restored).rejects.toThrow("Handling failed");
    expect(paymentline.payment_status).toBe("retry");
    expect(paymentInterface.requests[paymentline.uuid]).toBe(undefined);

    // No request left: "Check status" only removes the action
    paymentline.uiState.statusCheckNeeded = true;
    await paymentInterface.checkPaymentStatus(paymentline);
    expect(paymentline.uiState.statusCheckNeeded).toBe(undefined);
});

test("cancelPayment answered during its handler, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentInterface = new PaymentInterfaceV2(store, card);
    card.payment_interface = paymentInterface;
    const paymentline = createPaymentLine(store, order, card);
    paymentInterface.sendPaymentRequest = async (line, request) => request.wait("waiting_card");
    paymentInterface.sendPaymentCancel = async () => true;
    paymentInterface.handlePaymentCancelResponse = async (line) => {
        line.payment_status = "retry";
        paymentInterface.answerRequest(line, true);
        await Promise.resolve();
        return true;
    };

    const pay = paymentline.pay();
    expect(await paymentline.cancelPayment()).toBe(false);
    expect(await pay).toBe(true);
    expect(paymentline.payment_status).toBe("done");
});

test("adjust, PaymentInterfaceV2", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    card.payment_interface = new PaymentInterfaceV2(store, card);
    const paymentline = createPaymentLine(store, order, card);

    // the hooks receive the line itself, not its uuid
    card.payment_interface.canBeAdjusted = (line) => line === paymentline;
    expect(paymentline.canBeAdjusted()).toBe(true);
    card.payment_interface.sendPaymentAdjust = async (line) => line === paymentline;
    expect(await paymentline.adjustAmount(20)).toBe(true);
    expect(paymentline.getAmount()).toBe(30);
});
