import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";
import {
    postMessage,
    amountIs,
    ADD_PRODUCT_SELECTED,
    ORDER_IS_FINALIZED,
    NEW_ORDER,
} from "@point_of_sale/../tests/tours/customer_display_tour";

const QR_URL =
    "/report/barcode/QR/http%3A%2F%2Flocalhost%3A1740%2Fpos%2Fpay%2F6%3Faccess_token%3D5bb78d6c-bf8e-44ed-8de2-e4ae5b8696ec?width=200&height=200";

const PAY_ONLINE = {
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

const PAID = {
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

registry.category("web_tour.tours").add("CustomerDisplayTourOnlinePayment", {
    steps: () =>
        [
            {
                trigger: "div:contains('Welcome.')",
                run: () => {
                    window.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
                    postMessage(ADD_PRODUCT_SELECTED, "add product").run();
                },
            },
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            amountIs("Total", "2,972.75"),
            postMessage(PAY_ONLINE, "pay with cash"),
            {
                trigger: `.modal-content img[alt='QR Code to pay'][src='${QR_URL}']`,
            },
            postMessage(PAID, "payment approved"),
            postMessage(ORDER_IS_FINALIZED, "order is finalized"),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
                run: "click",
            },
            postMessage(NEW_ORDER, "new order"),
            {
                trigger: "div:contains('Welcome.')",
            },
            Order.doesNotHaveLine({}),
            amountIs("Total", "0.00"),

            // Make a new order
            postMessage(ADD_PRODUCT_SELECTED, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            amountIs("Total", "2,972.75"),
            postMessage(PAY_ONLINE, "pay with cash"),
            {
                trigger: `.modal-content img[alt='QR Code to pay'][src='${QR_URL}']`,
            },
        ].flat(),
});
