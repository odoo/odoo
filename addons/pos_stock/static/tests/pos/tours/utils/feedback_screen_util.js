/* global posmodel */
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";

export function checkTicketData(data, basic = false) {
    const check = async (data, basic) => {
        const order = posmodel.getOrder();
        const orderData = posmodel.ticketPrinter.getOrderReceiptData(order, basic);
        const iframe = await posmodel.ticketPrinter.generateIframe(
            "point_of_sale.pos_order_receipt",
            orderData
        );
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const ticket = doc.getElementById("pos-receipt");

        if (!ticket && !Object.keys(data).length) {
            return true;
        }
        if (data.is_shipping_date || data.is_shipping_date_today) {
            if (!ticket.querySelector(".shipping-date")) {
                throw new Error("No shipping date has been found in receipt.");
            }
            if (data.is_shipping_date_today) {
                const expectedDelivery = new Date().toLocaleString(
                    "en-US",
                    luxon.DateTime.DATE_SHORT
                );
                ticket.querySelector(".shipping-date").innerHTML.includes(expectedDelivery);
            }
        } else if (data.is_shipping_date === false) {
            if (ticket.querySelector(".shipping-date")) {
                throw new Error("A shipping date has been found in receipt.");
            }
        }
    };
    return [
        ...FeedbackScreen.checkTicketData(data, basic),
        {
            trigger: "body",
            run: async () => await check(data, basic),
        },
    ];
}
