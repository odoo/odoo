import { test, expect } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { mockDate } from "@odoo/hoot-mock";
import {
    getFilledOrder,
    mountPosDialog,
    setupPosEnv,
    mountCustomerDisplayWithOrder,
} from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { Chrome } from "@point_of_sale/app/pos_app";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { QrCodeCustomerDisplay } from "@point_of_sale/app/customer_display/customer_display_qr_code_popup";

definePosModels();

test("click order uses selected order for customer display dispatch", async () => {
    const store = await setupPosEnv();
    const firstOrder = await getFilledOrder(store);
    const secondOrder = await getFilledOrder(store);

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(firstOrder);
    ticketScreen.onClickOrder(secondOrder);

    let formattedOrder;
    let dispatchedData;
    patchWithCleanup(CustomerDisplayPosAdapter.prototype, {
        formatOrderData(order) {
            formattedOrder = order;
            this.data = {
                amount: order.currencyDisplayPriceIncl,
                lines: order.lines,
            };
        },
        setExtraData(extraData) {
            if (extraData) {
                Object.assign(this.data, extraData);
            }
        },
        dispatch() {
            dispatchedData = this.data;
        },
    });

    const fakeChrome = {
        pos: store,
        getCustomerDisplayExtraData() {
            return { screenName: "TicketScreen" };
        },
    };

    Chrome.prototype.sendOrderToCustomerDisplay.call(
        fakeChrome,
        { selectedOrder: ticketScreen.getSelectedOrder() },
        { current: "TicketScreen" }
    );

    expect(ticketScreen.getSelectedOrder().id).toBe(secondOrder.id);
    expect(formattedOrder.id).toBe(secondOrder.id);
    expect(dispatchedData.amount).toBe(secondOrder.currencyDisplayPriceIncl);
    expect(dispatchedData.screenName).toBe("TicketScreen");
});

test.tags("desktop");
test("customer display QR popup shows QR dialog from UI button", async () => {
    const store = await setupPosEnv();
    await mountPosDialog(QrCodeCustomerDisplay, {
        customerDisplayURL: `${store.config._base_url}/pos_customer_display/${store.config.id}/test-device`,
    });

    await contains("button:contains('Display QR')").click();
    await waitFor("#CustomerDisplayqrCode");

    const qrImage = queryOne("#CustomerDisplayqrCode");
    expect(qrImage.getAttribute("src").includes("data:image")).toBe(true);
});

test("customer display shows welcome states", async () => {
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({ finalized: false, lines: [] });
    expect(queryOne(".o_customer_display_main")).toHaveText("Welcome.\nPowered by");
});

test("customer display shows thank you states", async () => {
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({ finalized: true, lines: [] });
    expect(queryOne(".o_customer_display_main")).toHaveText("Thank you.\nPowered by");
});

test("customer display renders selected line, notes and total", async () => {
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({
        lines: [
            {
                productId: 5,
                productName: "Wall Shelf Unit",
                price: "$\u00a03.45",
                qty: "1",
                unit: "Units",
                unitPrice: "$\u00a03.45",
                discount: "0",
                customerNote: "No onions",
                internalNote: '[{"text":"VIP","colorIndex":2}]',
                packLotLines: [],
                price_without_discount: "$\u00a03.45",
                isSelected: true,
            },
        ],
        amount: "$\u00a03.45",
        amountTaxes: "$\u00a00.45",
        subtotal: "$\u00a03.00",
    });

    expect(queryOne(".orderline.selected .product-name")).toHaveText("Wall Shelf Unit");
    expect(queryOne(".customer-note")).toHaveText("No onions");
    expect(queryOne(".internal-note-container")).toHaveText("VIP");
    expect(queryOne(".o_customer_display_total")).toHaveText(
        "Subtotal\n$ 3.00\nTaxes\n$ 0.45\nTotal\n$ 3.45"
    );
});

test("customer display qrPaymentData merges both payloads", async () => {
    await setupPosEnv();
    const customerDisplay = await mountCustomerDisplayWithOrder({
        qrPaymentData: {
            amount: "$\u00a03.45",
            qrCode: "data:image/png;base64,aaa",
        },
        onlinePaymentData: {
            status: "pending",
        },
    });

    expect(customerDisplay.qrPaymentData.amount).toBe("$\u00a03.45");
    expect(customerDisplay.qrPaymentData.qrCode).toBe("data:image/png;base64,aaa");
    expect(customerDisplay.qrPaymentData.status).toBe("pending");
});

test("customer display screen saver", async () => {
    mockDate("2021-02-10 00:00:00");
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({
        displayScreenSaver: true,
    });

    expect(queryOne(".timer-date-container")).toHaveText("Wednesday\nFebruary, 10, 2021");
});
