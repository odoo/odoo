import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";
import { run } from "@point_of_sale/../tests/generic_helpers/utils";
import { isVisible } from "@web/core/utils/ui";

export function postMessage(message, description = "") {
    return run(() => {
        window.customerDisplayChannel.postMessage(
            typeof message === "string" ? JSON.parse(message) : message
        );
    }, `send message to customer display: ${description},  with value: ${message}`);
}

export function amountIs(method, amount) {
    return {
        content: `Check that the ${method} amount is ${amount}`,
        trigger: `div.row:has(div:contains('${method}')):has(div:contains('${amount}'))`,
    };
}
const ADD_PRODUCT =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":false,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":false,"amount":"2,972.75","paymentLines":[],"change":0,"onlinePaymentData":{}}';
export const ADD_PRODUCT_SELECTED =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":true,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":false,"amount":"2,972.75","paymentLines":[],"change":0,"onlinePaymentData":{}}';
export const ADD_MULTI_PRODUCTS = (() => {
    const count = 20;
    const lines = Array.from({ length: count }, (_, i) => {
        const price = (Math.random() * 100 + 1).toFixed(2);
        return {
            productName: `Product ${i + 1}`,
            price: `$${price}`,
            qty: "1.00",
            unit: "Units",
            unitPrice: `$${price}`,
            customerNote: "",
            internalNote: "[]",
            comboParent: "",
            packLotLines: [],
            price_without_discount: `$${price}`,
            isSelected: i === count - 1,
            imageSrc: "/web/image/product.product/855/image_128",
        };
    });
    const amount = lines
        .reduce((sum, line) => sum + parseFloat(line.price.replace("$", "")), 0)
        .toFixed(2);
    return JSON.stringify({
        lines,
        finalized: false,
        amount,
        paymentLines: [],
        change: 0,
        onlinePaymentData: {},
    });
})();
const PAY_WITH_CASH =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":true,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":false,"amount":"2,972.75","paymentLines":[{"name":"Cash","amount":"2,972.75"}],"change":0,"onlinePaymentData":{}}';
export const ORDER_IS_FINALIZED =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":false,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":true,"amount":"2,972.75","paymentLines":[{"name":"Cash","amount":"2,972.75"}],"change":0,"onlinePaymentData":{}}';
export const NEW_ORDER =
    '{"lines":[],"finalized":false,"amount":"0.00","paymentLines":[],"change":0,"onlinePaymentData":{}}';

const QR_URL =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

const PAY_WITH_CARD = {
    lines: [
        {
            productName: "Letter Tray",
            price: "$ 2,972.75",
            qty: "1.00",
            unit: "Units",
            unitPrice: "$ 2,972.75",
            oldUnitPrice: "",
            customerNote: "",
            internalNote: "",
            comboParent: "",
            packLotLines: [],
            price_without_discount: "$ 2,972.75",
            isSelected: true,
            imageSrc: "/web/image/product.product/855/image_128",
        },
    ],
    finalized: false,
    amount: "2,972.75",
    paymentLines: [{ name: "CARD", amount: "2,972.75" }],
    change: 0,
    onlinePaymentData: {},
    qrPaymentData: null,
};

const SEND_QR = {
    lines: [
        {
            productName: "Letter Tray",
            price: "$ 2,972.75",
            qty: "1.00",
            unit: "Units",
            unitPrice: "$ 2,972.75",
            oldUnitPrice: "",
            customerNote: "",
            internalNote: "",
            comboParent: "",
            packLotLines: [],
            price_without_discount: "$ 2,972.75",
            isSelected: true,
            imageSrc: "/web/image/product.product/855/image_128",
        },
    ],
    finalized: false,
    amount: "2,972.75",
    paymentLines: [{ name: "CARD", amount: "2,972.75" }],
    change: 0,
    onlinePaymentData: {},
    qrPaymentData: {
        amount: "$ 2,972.75",
        name: "CARD",
        qrCode: QR_URL,
    },
};

registry.category("web_tour.tours").add("CustomerDisplayTour", {
    steps: () =>
        [
            {
                trigger: "div:contains('Welcome.')",
                run: () => {
                    window.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
                    postMessage(ADD_PRODUCT, "add product").run();
                },
            },
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            {
                content: "An order line with `isSelected: false` should not have 'selected' class",
                trigger: ".order-container .orderline:last-child:not(.selected)",
            },
            amountIs("Total", "2,972.75"),
            postMessage(PAY_WITH_CASH, "pay with cash"),
            amountIs("Cash", "2,972.75"),
            postMessage(ORDER_IS_FINALIZED, "order is finalized"),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
            },
            postMessage(NEW_ORDER, "new order"),
            {
                trigger: " div:contains('Welcome.')",
            },
            Order.doesNotHaveLine({}),
            amountIs("Total", "0.00"),
            {
                trigger: "body",
                run: () => postMessage(ADD_PRODUCT_SELECTED, "add products").run(),
            },
            {
                content: "An order line with `isSelected: true` should have 'selected' class",
                trigger: ".order-container .orderline:last-child.selected",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("CustomerDisplayTourScroll", {
    steps: () =>
        [
            {
                trigger: "div:contains('Welcome.')",
                run: async () => {
                    window.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
                    postMessage(ADD_MULTI_PRODUCTS, "add 20 products").run();
                },
            },
            {
                content: "An order line with `isSelected: true` should have 'selected' class",
                trigger: ".order-container .orderline:last-child.selected",
                run: async () =>
                    await new Promise((resolve) => {
                        const orderLine = document.querySelector(
                            ".order-container .orderline:last-child.selected"
                        );
                        const animationDuration = parseFloat(
                            getComputedStyle(orderLine).animationDuration
                        );
                        if (animationDuration === 0) {
                            return resolve();
                        }
                        orderLine.onanimationend = function (event) {
                            if (event.target === orderLine && event.animationName === "item_in") {
                                resolve(event);
                            }
                        };
                    }),
            },
            {
                trigger: ".order-container",
                run: async () => {
                    const orderContainer = document.querySelector(".order-container");
                    const orderLine = document.querySelector(
                        ".order-container .orderline:last-child.selected"
                    );
                    await new Promise((resolve) => {
                        const checkScroll = () => {
                            requestAnimationFrame(() => {
                                if (orderContainer.scrollTop > 0 && isVisible(orderLine)) {
                                    resolve();
                                } else {
                                    setTimeout(checkScroll, 1000);
                                }
                            });
                        };
                        checkScroll();
                    });
                },
            },
        ].flat(),
});

registry.category("web_tour.tours").add("CustomerDisplayTourWithQr", {
    steps: () =>
        [
            {
                trigger: "div:contains('Welcome.')",
                run: () => {
                    window.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
                    postMessage(ADD_PRODUCT, "add product").run();
                },
            },
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            amountIs("Total", "2,972.75"),
            postMessage(PAY_WITH_CARD, "pay with card"),
            postMessage(SEND_QR, "send qr code"),
            { trigger: "img[alt='QR Code']" },
            postMessage(PAY_WITH_CARD, "confirm payment"),
            postMessage(ORDER_IS_FINALIZED, "order is finalized"),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
            },
        ].flat(),
});
