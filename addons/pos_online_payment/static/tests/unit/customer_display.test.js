import { test, expect } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { mountCustomerDisplayWithOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("CustomerDisplayTourOnlinePayment: formatOrderData includes online payment data", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.onlinePaymentData = {
        formattedAmount: "$ 17.85",
        qrCode: "https://example.com/qr",
        orderName: "Order 0001",
    };

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.onlinePaymentData).toEqual(order.onlinePaymentData);
});

test("CustomerDisplayTourOnlinePayment: formatOrderData reflects online payment lifecycle", async () => {
    const store = await setupPosEnv();
    const adapter = new CustomerDisplayPosAdapter();

    const order = store.addNewOrder();
    order.onlinePaymentData = {
        amount: "$ 2,972.75",
        qrCode: "https://example.com/qr-code",
        orderName: "Order 0001",
    };

    adapter.formatOrderData(order);
    expect(adapter.data.finalized).toBe(false);
    expect(adapter.data.onlinePaymentData.qrCode).toBe("https://example.com/qr-code");

    order.state = "paid";
    order.onlinePaymentData = {};
    adapter.formatOrderData(order);
    expect(adapter.data.finalized).toBe(true);
    expect(adapter.data.onlinePaymentData).toEqual({});

    const newOrder = store.addNewOrder();
    adapter.formatOrderData(newOrder);
    expect(adapter.data.finalized).toBe(false);
    expect(adapter.data.lines).toHaveLength(0);
    expect(adapter.data.amount).toBe("$\u00a00.00");
});

test("CustomerDisplayTourOnlinePayment: UI renders online payment QR card", async () => {
    const imgUri =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({
        amount: "$\u00a02,972.75",
        onlinePaymentData: {
            amount: "$\u00a02,972.75",
            qrCode: imgUri,
        },
    });

    const qrImage = queryOne(".qr-payment-card .qr-image[alt='QR Code']");
    expect(qrImage.getAttribute("src")).toBe(imgUri);
    expect(queryOne(".qr-payment-card")).toHaveText("Scan the QR for payment\nAmount: $ 2,972.75");
});
