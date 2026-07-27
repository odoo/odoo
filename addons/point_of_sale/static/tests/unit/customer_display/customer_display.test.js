import { test, expect } from "@odoo/hoot";
import { range } from "@web/core/utils/numbers";
import { queryOne, waitFor, animationFrame } from "@odoo/hoot-dom";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
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

    const adapter = new CustomerDisplayPosAdapter();
    const fakeChrome = {
        pos: store,
        adapter,
        dispatchDebounced() {
            adapter.dispatch(store);
        },
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
    expect(queryOne(".o_customer_display_main")).toHaveText("Welcome\nPowered by");
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

test("CustomerDisplayTour: full customer display flow with products and payments", async () => {
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({
        lines: [
            {
                productName: "Letter Tray",
                price: "$ 2,972.75",
                qty: "1.00",
                unit: "Units",
                unitPrice: "$ 2,972.75",
                customerNote: "",
                internalNote: "[]",
                comboParent: "",
                packLotLines: [],
                price_without_discount: "$ 2,972.75",
                isSelected: false,
                imageSrc: "/web/image/product.product/855/image_128",
            },
        ],
        finalized: false,
        amount: "$ 2,972.75",
        paymentLines: [],
        change: 0,
        onlinePaymentData: {},
    });

    expect(queryOne(".order-container .orderline:last-child")).not.toHaveClass("selected");
    expect(queryOne(".order-container .orderline .product-name")).toHaveText("Letter Tray");

    const totalRow = [...document.querySelectorAll("div.row")].find((r) =>
        r.textContent.includes("Total")
    );
    expect(totalRow).not.toBe(null);
    expect(totalRow.textContent).toInclude("2,972.75");

    const customerDisplayData = getService("customer_display_data");
    Object.assign(customerDisplayData, {
        lines: [
            {
                productName: "Letter Tray",
                price: "$ 2,972.75",
                qty: "1.00",
                unit: "Units",
                unitPrice: "$ 2,972.75",
                customerNote: "",
                internalNote: "[]",
                comboParent: "",
                packLotLines: [],
                price_without_discount: "$ 2,972.75",
                isSelected: true,
                imageSrc: "/web/image/product.product/855/image_128",
            },
        ],
        finalized: false,
        amount: "$ 2,972.75",
        paymentLines: [{ name: "Cash", amount: "2,972.75" }],
        change: 0,
        onlinePaymentData: {},
    });
    await animationFrame();

    const cashRow = [...document.querySelectorAll("div.row")].find((r) =>
        r.textContent.includes("Cash")
    );
    expect(cashRow).not.toBe(null);
    expect(cashRow.textContent).toInclude("2,972.75");

    Object.assign(customerDisplayData, {
        finalized: true,
    });
    await animationFrame();
    await waitFor(".feedback-summary");
    Object.assign(customerDisplayData, {
        lines: [],
        finalized: false,
        amount: "$ 0.00",
        paymentLines: [],
        change: 0,
        onlinePaymentData: {},
    });
    await animationFrame();

    expect(document.querySelector(".order-container .orderline")).toBe(null);
    Object.assign(customerDisplayData, {
        lines: [
            {
                productName: "Letter Tray",
                price: "$ 2,972.75",
                qty: "1.00",
                unit: "Units",
                unitPrice: "$ 2,972.75",
                customerNote: "",
                internalNote: "[]",
                comboParent: "",
                packLotLines: [],
                price_without_discount: "$ 2,972.75",
                isSelected: true,
                imageSrc: "/web/image/product.product/855/image_128",
            },
        ],
        finalized: false,
        amount: "$ 2,972.75",
        paymentLines: [],
        change: 0,
        onlinePaymentData: {},
    });
    await animationFrame();
    expect(queryOne(".order-container .orderline:last-child")).toHaveClass("selected");
    Object.assign(customerDisplayData, {
        displayScreenSaver: true,
    });
    await animationFrame();
    await waitFor(".login-overlay");
});

test("CustomerDisplayTourScroll: customer display scrolls to selected orderline", async () => {
    await setupPosEnv();

    const count = 20;
    const lines = range(1, count + 1).map((i) => ({
        productName: `Product ${i}`,
        price: `$ ${(Math.random() * 100 + 1).toFixed(2)}`,
        qty: "1.00",
        unit: "Units",
        unitPrice: `$ ${(Math.random() * 100 + 1).toFixed(2)}`,
        customerNote: "",
        internalNote: "[]",
        comboParent: "",
        packLotLines: [],
        price_without_discount: `$ ${(Math.random() * 100 + 1).toFixed(2)}`,
        isSelected: i === count,
        imageSrc: "/web/image/product.product/855/image_128",
    }));

    await mountCustomerDisplayWithOrder({
        lines,
        finalized: false,
        amount: "$ 1000.00",
        paymentLines: [],
        change: 0,
        onlinePaymentData: {},
    });

    const selectedLine = document.querySelector(".order-container .orderline:last-child.selected");
    expect(selectedLine).not.toBe(null);
    expect(selectedLine.textContent).toInclude(`Product ${count}`);

    const orderContainer = document.querySelector(".order-container");
    await new Promise((resolve) => {
        const checkScroll = () => {
            requestAnimationFrame(() => {
                if (orderContainer.scrollTop > 0 && selectedLine.getBoundingClientRect().top >= 0) {
                    resolve();
                } else {
                    setTimeout(checkScroll, 100);
                }
            });
        };
        checkScroll();
    });
    expect(orderContainer.scrollTop).toBeGreaterThan(0);
});

test("CustomerDisplayTourWithQr: customer display shows QR code for payment", async () => {
    await setupPosEnv();

    const QR_URL =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

    await mountCustomerDisplayWithOrder({
        lines: [
            {
                productName: "Letter Tray",
                price: "$ 2,972.75",
                qty: "1.00",
                unit: "Units",
                unitPrice: "$ 2,972.75",
                customerNote: "",
                internalNote: "[]",
                comboParent: "",
                packLotLines: [],
                price_without_discount: "$ 2,972.75",
                isSelected: true,
                imageSrc: "/web/image/product.product/855/image_128",
            },
        ],
        finalized: false,
        amount: "$ 2,972.75",
        paymentLines: [{ name: "CARD", amount: "2,972.75" }],
        change: 0,
        onlinePaymentData: {},
        qrPaymentData: null,
    });

    expect(queryOne(".order-container .orderline .product-name")).toHaveText("Letter Tray");
    const customerDisplayData = getService("customer_display_data");
    Object.assign(customerDisplayData, {
        qrPaymentData: {
            amount: "$ 2,972.75",
            qrCode: QR_URL,
        },
    });
    await animationFrame();
    const qrImg = document.querySelector("img[alt='QR Code']");
    expect(qrImg).not.toBe(null);
    Object.assign(customerDisplayData, {
        qrPaymentData: null,
    });
    await animationFrame();
    Object.assign(customerDisplayData, {
        finalized: true,
    });
    await animationFrame();
    await waitFor(".feedback-summary");
});
