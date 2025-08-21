import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as CustomerDisplay from "@point_of_sale/../tests/customer_display/customer_display_utils";
import { registry } from "@web/core/registry";
import { isVisible } from "@web/core/utils/ui";

registry.category("web_tour.tours").add("CustomerDisplayTour", {
    steps: () =>
        [
            CustomerDisplay.addProduct(CustomerDisplay.ADD_PRODUCT, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            {
                content: "An order line with `isSelected: false` should not have 'selected' class",
                trigger: ".order-container .orderline:last-child:not(.selected)",
            },
            CustomerDisplay.amountIs("Total", "2,972.75"),
            CustomerDisplay.postMessage(CustomerDisplay.PAY_WITH_CASH, "pay with cash"),
            CustomerDisplay.amountIs("Cash", "2,972.75"),
            CustomerDisplay.postMessage(CustomerDisplay.ORDER_IS_FINALIZED, "order is finalized"),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
            },
            CustomerDisplay.postMessage(CustomerDisplay.NEW_ORDER, "new order"),
            {
                trigger: " div:contains('Welcome.')",
            },
            Order.doesNotHaveLine({}),
            CustomerDisplay.amountIs("Total", "0.00"),
            {
                trigger: "body",
                run: () =>
                    CustomerDisplay.postMessage(
                        CustomerDisplay.ADD_PRODUCT_SELECTED,
                        "add products"
                    ).run(),
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
            CustomerDisplay.addProduct(CustomerDisplay.ADD_MULTI_PRODUCTS, "add 20 products"),
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
                content: "The order container should have scrolled to show the selected order line",
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
            CustomerDisplay.addProduct(CustomerDisplay.ADD_PRODUCT, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            CustomerDisplay.amountIs("Total", "2,972.75"),
            CustomerDisplay.postMessage(CustomerDisplay.PAY_WITH_CARD, "pay with card"),
            CustomerDisplay.postMessage(CustomerDisplay.SEND_QR, "send qr code"),
            { trigger: "img[alt='QR Code']" },
            CustomerDisplay.postMessage(CustomerDisplay.PAY_WITH_CARD, "confirm payment"),
            CustomerDisplay.postMessage(CustomerDisplay.ORDER_IS_FINALIZED, "order is finalized"),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
            },
        ].flat(),
});
