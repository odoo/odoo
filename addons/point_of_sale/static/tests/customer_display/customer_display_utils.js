import { run } from "@point_of_sale/../tests/generic_helpers/utils";

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

export function addProduct(product, description = "") {
    return {
        trigger: "div:contains('Welcome.')",
        run: async () => {
            window.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
            postMessage(product, description).run();
        },
    };
}

export const ADD_PRODUCT =
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

export const PAY_WITH_CASH =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":true,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":false,"amount":"2,972.75","paymentLines":[{"name":"Cash","amount":"2,972.75"}],"change":0,"onlinePaymentData":{}}';

export const ORDER_IS_FINALIZED =
    '{"lines":[{"productName":"Letter Tray","price":"$ 2,972.75","qty":"1.00","unit":"Units","unitPrice":"$ 2,972.75","customerNote":"","internalNote":"[]","comboParent":"","packLotLines":[],"price_without_discount":"$ 2,972.75","isSelected":false,"imageSrc":"/web/image/product.product/855/image_128"}],"finalized":true,"amount":"2,972.75","paymentLines":[{"name":"Cash","amount":"2,972.75"}],"change":0,"onlinePaymentData":{}}';

export const NEW_ORDER =
    '{"lines":[],"finalized":false,"amount":"0.00","paymentLines":[],"change":0,"onlinePaymentData":{}}';

export const QR_URL =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

export const PAY_WITH_CARD = {
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

export const SEND_QR = {
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

export const PAY_ONLINE = {
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
    paymentLines: [{ name: "ONLINE", amount: "2,972.75" }],
    change: 0,
    onlinePaymentData: {
        formattedAmount: "$ 2,972.75",
        orderName: "/",
        qrCode: QR_URL,
    },
};

export const PAID = {
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
    paymentLines: [{ name: "ONLINE", amount: "2,972.75" }],
    change: 0,
    onlinePaymentData: {},
};
