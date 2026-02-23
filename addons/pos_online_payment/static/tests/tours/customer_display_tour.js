import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as CustomerDisplay from "@point_of_sale/../tests/customer_display/customer_display_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("CustomerDisplayTourOnlinePayment", {
    steps: () =>
        [
            CustomerDisplay.addProduct(CustomerDisplay.ADD_PRODUCT_SELECTED, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            CustomerDisplay.amountIs("Total", "2,972.75"),
            CustomerDisplay.postMessage(CustomerDisplay.PAY_ONLINE, "pay with cash"),
            {
                trigger: `.modal-content img[alt='QR Code to pay'][src='${CustomerDisplay.QR_URL}']`,
            },
            CustomerDisplay.postMessage(CustomerDisplay.PAID, "payment approved"),
            CustomerDisplay.postMessage(CustomerDisplay.ORDER_IS_FINALIZED, "order is finalized"),
            negateStep(Dialog.is()),
            {
                content: "Check that we are now on the 'Thank you' screen",
                trigger: "div:contains('Thank you.')",
                run: "click",
            },
            CustomerDisplay.postMessage(CustomerDisplay.NEW_ORDER, "new order"),
            {
                trigger: "div:contains('Welcome.')",
            },
            Order.doesNotHaveLine({}),
            CustomerDisplay.amountIs("Total", "0.00"),

            // Make a new order
            CustomerDisplay.postMessage(CustomerDisplay.ADD_PRODUCT_SELECTED, "add product"),
            Order.hasLine({ productName: "Letter Tray", price: "2,972.75" }),
            CustomerDisplay.amountIs("Total", "2,972.75"),
            CustomerDisplay.postMessage(CustomerDisplay.PAY_ONLINE, "pay with cash"),
            {
                trigger: `.modal-content img[alt='QR Code to pay'][src='${CustomerDisplay.QR_URL}']`,
            },
        ].flat(),
});
