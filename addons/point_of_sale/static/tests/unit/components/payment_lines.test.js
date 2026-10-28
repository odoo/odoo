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

describe("getPaymentActionState", () => {
    const setup = async () => {
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
            },
        });
        return { comp, card, paymentline };
    };

    const normalizeActionState = (state) => {
        state.actions = state.actions.map(normalizeFunctionsInObject);
        return state;
    };

    test("payment", async () => {
        const { comp, paymentline } = await setup();

        // No status
        const stateNoStatus = comp.getPaymentActionState(paymentline);
        expect(stateNoStatus).toBe(null);

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
            title: "Transaction failed",
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
            icon: "autorenew",
            iconClass: "oi-spin",
            title: "Connection error",
            actions: [
                {
                    id: "force_done",
                    label: "Force done",
                    action: "function",
                    severity: "warning",
                },
                {
                    id: "force_cancel",
                    label: "Force Cancel",
                    action: "function",
                    severity: "danger",
                },
            ],
        });

        // waiting_card
        paymentline.payment_status = "waiting_card";
        const stateWaitingCardNoRefund = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaitingCardNoRefund)).toEqual({
            id: "waiting_card",
            icon: "autorenew",
            iconClass: "oi-spin",
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
                },
            ],
        });

        // waiting_scan
        paymentline.payment_status = "waiting_scan";
        const stateWaitingScan = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaitingScan)).toEqual({
            id: "waiting_scan",
            icon: "autorenew",
            iconClass: "oi-spin",
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
                },
            ],
        });

        // waiting
        paymentline.payment_status = "waiting";
        const stateWaiting = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaiting)).toEqual({
            id: "waiting",
            icon: "autorenew",
            iconClass: "oi-spin",
            title: "Request sent",
            actions: [
                {
                    id: "force_done",
                    label: "Force done",
                    action: "function",
                    severity: "warning",
                },
            ],
        });

        // waiting_cancel
        paymentline.payment_status = "waiting_cancel";
        const stateWaitingCancel = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaitingCancel)).toEqual({
            id: "waiting_cancel",
            icon: "autorenew",
            iconClass: "oi-spin",
            title: "Request sent",
            actions: [
                {
                    id: "force_cancel",
                    label: "Force Cancel",
                    action: "function",
                    severity: "danger",
                },
            ],
        });

        // waiting_capture
        paymentline.payment_status = "waiting_capture";
        const stateWaitingCapture = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaitingCapture)).toEqual({
            id: "waiting_capture",
            icon: "autorenew",
            iconClass: "oi-spin",
            title: "Request sent",
            actions: [],
        });

        // done
        paymentline.payment_status = "done";
        const stateDoneNoRefund = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateDoneNoRefund)).toEqual({
            id: "done",
            title: "Payment Successful",
            actions: [],
        });
    });

    test("refund", async () => {
        const { comp, card, paymentline } = await setup();

        // waiting_card
        paymentline.payment_status = "waiting_card";
        const stateWaitingCardRefund = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateWaitingCardRefund)).toEqual({
            id: "waiting_card",
            icon: "autorenew",
            iconClass: "oi-spin",
            title: "Refund in process",
            actions: [
                {
                    id: "force_done",
                    label: "Force done",
                    action: "function",
                    severity: "warning",
                },
            ],
        });

        // done
        paymentline.payment_status = "done";
        const stateDoneRefund = comp.getPaymentActionState(paymentline);
        expect(normalizeActionState(stateDoneRefund)).toEqual({
            id: "done",
            title: "Refund Successful",
            actions: [],
        });

        // refund_available
        paymentline.payment_status = null;
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
});

test("getLineControls", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cash = store.models["pos.payment.method"].get(1);
    const card = store.models["pos.payment.method"].get(2);
    const cashline = createPaymentLine(store, order, cash);
    const paymentline = createPaymentLine(store, order, card, { payment_status: "waiting_card" });
    const comp = await mountWithCleanup(PaymentScreenPaymentLines, {
        props: {
            paymentLines: [cashline, paymentline],
            deleteLine: () => {},
            selectLine: () => {},
            sendForceDone: () => {},
            sendForceCancel: () => {},
            sendPaymentCancel: () => {},
            sendPaymentRequest: () => {},
            updateSelectedPaymentline: () => {},
        },
    });

    // Helpers
    const controls = (line) => {
        const { start, end } = comp.getLineControls(line);
        return {
            start: start.map(normalizeFunctionsInObject),
            end: end.map(normalizeFunctionsInObject),
        };
    };
    const qrCode = (disabled) => ({
        id: "qr_code",
        icon: "qr_code",
        classes: "paymentline_show_qr_code ms-2 ps-3",
        title: "Show QR Code",
        action: "function",
        disabled,
    });
    const spinner = {
        id: "spinner",
        icon: "autorenew",
        iconClass: "oi-spin",
        classes: "payment-spinner mx-2 px-3",
    };
    const deleteButton = {
        id: "delete",
        icon: "close_small",
        iconClass: "text-danger",
        classes: "delete-button mx-2 px-3",
        title: "Delete",
        action: "function",
    };

    // No status
    expect(controls(cashline)).toEqual({ start: [], end: [deleteButton] });

    // Not selected: a processing line shows the spinner
    const notSelected = {
        pending: [deleteButton],
        retry: [deleteButton],
        waiting: [spinner],
        waiting_card: [spinner],
        waiting_scan: [spinner],
        waiting_capture: [spinner],
        waiting_cancel: [spinner],
        force_done: [spinner],
        done: [],
    };
    for (const [status, end] of Object.entries(notSelected)) {
        paymentline.payment_status = status;
        expect(controls(paymentline)).toEqual({ start: [], end });
    }

    // Selected: the delete button shows when the line is deletable
    order.uiState.selected_paymentline_uuid = paymentline.uuid;
    const selected = {
        pending: [deleteButton],
        retry: [deleteButton],
        waiting: [deleteButton],
        waiting_card: [deleteButton],
        waiting_scan: [deleteButton],
        waiting_capture: [deleteButton],
        waiting_cancel: [],
        force_done: [deleteButton],
        done: [],
    };
    for (const [status, end] of Object.entries(selected)) {
        paymentline.payment_status = status;
        expect(controls(paymentline)).toEqual({ start: [], end });
    }
    order.uiState.selected_paymentline_uuid = null;

    // QR code: enabled only while processing with a QR code
    card.payment_method_type = "external_qr";
    paymentline.qr_code = "https://example.com/qr-code-data";
    paymentline.payment_status = "waiting_scan";
    expect(controls(paymentline)).toEqual({ start: [qrCode(false)], end: [spinner] });

    paymentline.payment_status = "done";
    expect(controls(paymentline)).toEqual({ start: [qrCode(true)], end: [] });

    paymentline.qr_code = null;
    paymentline.payment_status = "pending";
    expect(controls(paymentline)).toEqual({ start: [qrCode(true)], end: [deleteButton] });
});
