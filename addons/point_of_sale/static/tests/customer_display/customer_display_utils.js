/* global displayData */

import { run } from "@point_of_sale/../tests/generic_helpers/utils";
import { range } from "@web/core/utils/numbers";
import { uuidv4 } from "@point_of_sale/utils";

export function postMessage(message, description = "") {
    return run(() => {
        displayData._onDataReceived(
            typeof message !== "string" ? JSON.stringify(message) : message
        );
    }, `send message to customer display: ${description},  with value: ${message}`);
}

export function amountIs(method, amount) {
    return {
        content: `Check that the ${method} amount is ${amount}`,
        trigger: `div.row:has(div:contains('${method}')):has(div:contains('${amount}'))`,
    };
}

export const initOrderData = {
    order: {
        state: "draft",
        general_customer_note: "",
        internal_note: "",
    },

    extra_data: {
        prices: {
            subtotal_amount: 0,
            tax_amount: 0,
            total_amount: 0,
        },
    },

    lines: [],
    payments: [],
    change: 0,
    amount: 0,
    displayScreenSaver: false,
    onlinePaymentData: null,
};

export const getLineJsonData = (payload = {}) => {
    const price = Number(payload.price ?? 2972.75);
    const priceStr = "$ " + new Intl.NumberFormat().format(price);
    const id = String(Math.floor(Math.random() * 1000));

    return {
        id,
        uuid: id,
        combo_parent_id: false,
        product_id: 855,
        full_product_name: payload.name || "Letter Tray",
        price_subtotal_incl: priceStr,
        qty: 1,
        unit_price: priceStr,
        product_uom_name: "Units",
        price_unit: price,
        discount: 0,
        displayPriceNoDiscount: priceStr,
        customer_note: "",
        note: "",
        lot_names: [],
        ...payload,
    };
};

export const getPaymentJsonData = (payload = {}) => {
    const amount = Number(payload.amount ?? 2972.75);
    const amountStr = "$ " + new Intl.NumberFormat().format(amount);

    return {
        payment_method_data: {
            name: payload.name || "Cash",
            ...(payload.methodData || {}),
        },
        amount: amountStr,
        ...payload,
    };
};

export const getOrderJsonData = (payload = {}) => {
    const lines = payload.lines || [];
    const subtotal = lines.reduce((sum, l) => sum + (l.price_unit || 0), 0);
    const subtotalStr = "$ " + new Intl.NumberFormat().format(subtotal);
    return {
        payloadHash: uuidv4(),
        ...initOrderData,
        lines,
        extra_data: {
            prices: {
                subtotal_amount: subtotalStr,
                tax_amount: 0,
                total_amount: subtotalStr,
            },
        },
        payments: payload.payments || [],
        change: payload.change || 0,
        amount: subtotal,
        ...payload,
        order: {
            ...initOrderData.order,
            ...(payload.orderData || {}),
        },
        selectedLineUuid: payload.selected && lines.at(-1).uuid,
    };
};

export function startCustomerDisplay() {
    return {
        content: "init customer display",
        trigger: "div:contains('Welcome.')",
        run: () => postMessage(initOrderData).run(),
    };
}

export function addProduct(product, description = "") {
    return {
        trigger: "div:contains('Welcome')",
        run: async () => {
            postMessage(product, description).run();
        },
    };
}

export const ADD_PRODUCT = JSON.stringify(
    getOrderJsonData({
        lines: [getLineJsonData()],
    })
);

export const ADD_PRODUCT_SELECTED = JSON.stringify(
    getOrderJsonData({
        lines: [getLineJsonData()],
        selected: true,
    })
);

export const ADD_MULTI_PRODUCTS = (() => {
    const count = 20;
    const lines = range(1, count + 1).map((i) =>
        getLineJsonData({
            price: +(Math.random() * 100 + 1).toFixed(2),
            name: `Product ${i}`,
        })
    );

    return JSON.stringify(
        getOrderJsonData({
            lines,
            selected: true,
        })
    );
})();

export const PAY_WITH_CASH = JSON.stringify(
    getOrderJsonData({
        lines: [getLineJsonData()],
        payments: [getPaymentJsonData()],
    })
);

export const ORDER_IS_FINALIZED = JSON.stringify(
    getOrderJsonData({
        lines: [getLineJsonData()],
        payments: [getPaymentJsonData()],
        orderData: {
            state: "paid",
        },
        selected: true,
    })
);

export const NEW_ORDER = JSON.stringify(getOrderJsonData());

export const QR_URL =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

export const SEND_QR = JSON.stringify(
    getOrderJsonData({
        lines: [getLineJsonData()],
        payments: [
            getPaymentJsonData({
                name: "Cash",
            }),
        ],
        qrPaymentData: {
            amount: "$ 2972.75",
            qrCode: QR_URL,
        },
        selected: true,
    })
);

export const PAY_ONLINE = (() => {
    const lines = [getLineJsonData()];
    const total = lines.reduce((sum, l) => sum + l.price_unit, 0);

    return JSON.stringify(
        getOrderJsonData({
            lines,
            payments: [
                getPaymentJsonData({
                    name: "ONLINE",
                    amount: total,
                }),
            ],
            onlinePaymentData: {
                formattedAmount: `$ ${total}`,
                orderName: "/",
                qrCode: QR_URL,
            },
            selected: true,
        })
    );
})();

export const SCREENSAVER = JSON.stringify({
    ...initOrderData.order,
    displayScreenSaver: true,
});
