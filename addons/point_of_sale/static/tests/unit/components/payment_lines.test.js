import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    setupPosEnv,
    getFilledOrder,
    createPaymentLine,
    normalizeFunctionsInObject,
} from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

definePosModels();

test("getPaymentActionState", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const paymentline = createPaymentLine(store, order, card);
    const comp = await mountWithCleanup(PaymentScreenPaymentLines, {
        props: {
            paymentLines: [paymentline],
            deleteLine: () => {},
            selectLine: () => {},
            sendForceDone: () => {},
            sendForceCancel: () => {},
            sendPaymentCancel: () => {},
            sendPaymentRequest: () => {},
            updateSelectedPaymentline: () => {},
            isRefundOrder: false,
        },
    });

    // Helper
    const normalizeActionState = (state) => {
        state.actions = state.actions.map(normalizeFunctionsInObject);
        return state;
    };

    // No status
    const stateNoStatus = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateNoStatus)).toEqual({
        id: "unknown",
        title: "",
        actions: [],
    });

    // pending
    paymentline.payment_status = "pending";
    const statePending = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(statePending)).toEqual({
        id: "pending",
        title: "Payment request pending",
        actions: [
            {
                id: "send",
                label: "Send",
                title: "Send Payment Request",
                action: "function",
                severity: "primary",
            },
        ],
    });

    // retry
    paymentline.payment_status = "retry";
    const stateRetry = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateRetry)).toEqual({
        id: "retry",
        title: "Transaction cancelled",
        actions: [
            {
                id: "retry",
                label: "Retry",
                title: "Retry Payment Request",
                action: "function",
                severity: "primary",
            },
        ],
    });

    // force_done
    paymentline.payment_status = "force_done";
    const stateForceDone = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateForceDone)).toEqual({
        id: "force_done",
        title: "Connection error",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
            },
        ],
    });

    // waitingCard - refund
    paymentline.payment_status = "waitingCard";
    comp.props.isRefundOrder = true;
    const stateWaitingCardRefund = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaitingCardRefund)).toEqual({
        id: "waiting_refund",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Refund in process",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
            },
            {
                id: "cancel",
                label: "Cancel",
                title: "Send Cancel Request",
                action: "function",
                severity: "danger",
                show: false,
            },
        ],
    });

    // waitingCard - no refund
    comp.props.isRefundOrder = false;
    const stateWaitingCardNoRefund = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaitingCardNoRefund)).toEqual({
        id: "waiting_card",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Waiting for card",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
            },
            {
                id: "cancel",
                label: "Cancel",
                title: "Send Cancel Request",
                action: "function",
                severity: "danger",
                show: true,
            },
        ],
    });

    // waitingScan
    paymentline.payment_status = "waitingScan";
    const stateWaitingScan = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaitingScan)).toEqual({
        id: "waiting_scan",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Waiting for the customer to scan the QR Code",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
            },
            {
                id: "cancel",
                label: "Cancel",
                title: "Send Cancel Request",
                action: "function",
                severity: "danger",
                show: true,
            },
        ],
    });

    // waiting
    paymentline.payment_status = "waiting";
    const stateWaiting = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaiting)).toEqual({
        id: "waiting",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Request sent",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
                show: true,
            },
            {
                id: "force_cancel",
                label: "Force Cancel",
                action: "function",
                severity: "danger",
                show: false,
            },
        ],
    });

    // waitingCancel
    paymentline.payment_status = "waitingCancel";
    const stateWaitingCancel = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaitingCancel)).toEqual({
        id: "waiting_cancel",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Request sent",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
                show: false,
            },
            {
                id: "force_cancel",
                label: "Force Cancel",
                action: "function",
                severity: "danger",
                show: true,
            },
        ],
    });

    // waitingCapture
    paymentline.payment_status = "waitingCapture";
    const stateWaitingCapture = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateWaitingCapture)).toEqual({
        id: "waiting_capture",
        icon: "fa fa-circle-o-notch fa-spin",
        title: "Request sent",
        actions: [
            {
                id: "force_done",
                label: "Force done",
                action: "function",
                severity: "warning",
                show: false,
            },
            {
                id: "force_cancel",
                label: "Force Cancel",
                action: "function",
                severity: "danger",
                show: false,
            },
        ],
    });

    // Done - refund
    paymentline.payment_status = "done";
    comp.props.isRefundOrder = true;
    const stateDoneRefund = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateDoneRefund)).toEqual({
        id: "refunded",
        title: "Refund Successful",
        actions: [],
    });

    // Done - no refund
    comp.props.isRefundOrder = false;
    const stateDoneNoRefund = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateDoneNoRefund)).toEqual({
        id: "paid",
        title: "Payment Successful",
        actions: [],
    });

    // Refund available
    paymentline.payment_status = null;
    comp.props.isRefundOrder = true;
    card.payment_interface = true;
    const stateRefundAvailable = comp.getPaymentActionState(paymentline);
    expect(normalizeActionState(stateRefundAvailable)).toEqual({
        id: "refund_available",
        title: "Refund available",
        actions: [
            {
                id: "refund",
                label: "Refund",
                title: "Send Refund Request",
                action: "function",
                severity: "primary",
            },
        ],
    });
});

describe("show qr code button", () => {
    test("processing qr code", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_method_id.payment_method_type = "external_qr";
        paymentline.qr_code = "https://example.com/qr-code-data";
        paymentline.payment_status = "waitingScan";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline .paymentline_show_qr_code").not.toHaveAttribute("disabled");
    });

    test("non-processing qr code", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_method_id.payment_method_type = "external_qr";
        paymentline.qr_code = "https://example.com/qr-code-data";
        paymentline.payment_status = "done";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline .paymentline_show_qr_code").toHaveAttribute("disabled");
    });

    test("no qr code", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_method_id.payment_method_type = "external_qr";
        paymentline.qr_code = null;
        paymentline.payment_status = "pending";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline .paymentline_show_qr_code").toHaveAttribute("disabled");
    });

    test("not external qr code", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_method_id.payment_method_type = "none";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline .paymentline_show_qr_code").toHaveCount(0);
    });
});

describe("spinner or delete button", () => {
    test("not selected and no status", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(0);
        expect(".paymentline button.delete-button").toHaveCount(1);
    });

    test("selected but no status", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        order.uiState.selected_paymentline_uuid = paymentline.uuid;

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(0);
        expect(".paymentline button.delete-button").toHaveCount(1);
    });

    test("not selected but processing", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_status = "waitingCard";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(1);
        expect(".paymentline button.delete-button").toHaveCount(0);
    });

    test("not selected and not done", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_status = "pending";

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(0);
        expect(".paymentline button.delete-button").toHaveCount(1);
    });

    test("selected and processing", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_status = "waitingCard";
        order.uiState.selected_paymentline_uuid = paymentline.uuid;

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(0);
        expect(".paymentline button.delete-button").toHaveCount(1);
    });

    test("selected and done", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const card = store.models["pos.payment.method"].get(2);
        const paymentline = createPaymentLine(store, order, card);

        paymentline.payment_status = "done";
        order.uiState.selected_paymentline_uuid = paymentline.uuid;

        await mountWithCleanup(PaymentScreenPaymentLines, {
            props: {
                paymentLines: [paymentline],
                deleteLine: () => {},
                selectLine: () => {},
                sendForceDone: () => {},
                sendForceCancel: () => {},
                sendPaymentCancel: () => {},
                sendPaymentRequest: () => {},
                updateSelectedPaymentline: () => {},
                isRefundOrder: false,
            },
        });
        expect(".paymentline i.fa-circle-o-notch.fa-spin").toHaveCount(0);
        expect(".paymentline button.delete-button").toHaveCount(0);
    });
});
