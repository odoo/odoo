import { expect, mockUserAgent, test, waitUntil } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

const ORDER_CODE = "9315097989016751";

/**
 * Refund, through the Viva.com Android app, an order paid with the given method.
 * Returns the parameters of the URL that opens the app.
 */
const refundInVivaApp = async (originalPaymentMethodName, orderCode) => {
    mockUserAgent("android");
    localStorage.setItem("vivawallet_app_answer", "true");
    let appUrl = null;
    patch(window, {
        open(url) {
            appUrl = url;
        },
    });
    const lookups = [];
    onRpc("pos.payment", "viva_com_get_order_code", ({ args }) => {
        lookups.push(args[0]);
        return orderCode;
    });

    const store = await setupPosEnv();
    const paymentMethods = store.models["pos.payment.method"];
    const vivaPm = paymentMethods.find((pm) => pm.use_payment_terminal === "viva_com");
    const originalPm = paymentMethods.find((pm) => pm.name === originalPaymentMethodName);

    const original = await getFilledOrder(store);
    original.addPaymentline(originalPm).data.transaction_id = "original-transaction-id";
    await store.syncAllOrders({ orders: [original] });

    const refund = store.addNewOrder();
    refund.is_refund = true;
    const originalLine = original.lines[0];
    store.models["pos.order.line"].create({
        qty: -1,
        price_unit: originalLine.price_unit,
        product_id: originalLine.product_id,
        order_id: refund,
        tax_ids: originalLine.tax_ids.map((tax) => ["link", tax]),
        refunded_orderline_id: originalLine,
        price_type: "automatic",
    });

    const screen = await mountWithCleanup(PaymentScreen, { props: { orderUuid: refund.uuid } });
    await screen.addNewPaymentLine(vivaPm);
    await waitUntil(() => appUrl);
    return {
        params: new URL(appUrl).searchParams,
        originalPayment: original.payment_ids[0],
        refundPayment: refund.payment_ids[0],
        lookups,
    };
};

test("app refund of a Viva.com payment cancels the original transaction", async () => {
    const { params, originalPayment, refundPayment, lookups } = await refundInVivaApp(
        "Viva",
        ORDER_CODE
    );
    expect(lookups).toEqual([[originalPayment.id]]);
    expect(params.get("action")).toBe("cancel");
    expect(params.get("orderCode")).toBe(ORDER_CODE);
    expect(params.get("clientTransactionId")).toBe(refundPayment.viva_com_session_id);
});

test("app refund falls back to an unreferenced refund without an order code", async () => {
    const { params } = await refundInVivaApp("Viva", false);
    expect(params.get("action")).toBe("unreferenced_refund");
    expect(params.has("orderCode")).toBe(false);
});

test("app refund of an order not paid with Viva.com is unreferenced", async () => {
    const { params, lookups } = await refundInVivaApp("Cash", ORDER_CODE);
    expect(lookups).toEqual([]);
    expect(params.get("action")).toBe("unreferenced_refund");
    expect(params.has("orderCode")).toBe(false);
});
