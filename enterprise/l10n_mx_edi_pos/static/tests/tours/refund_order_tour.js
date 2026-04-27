import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";

registry.category("web_tour.tours").add("l10n_mx_edi_pos.tour_refund_discount_order", {
    steps: () => [
        {
            content: "Click the POS icon",
            trigger: ".o_app[data-menu-xmlid='point_of_sale.menu_point_root']",
            run: "click",
        },
        {
            content: "Open POS session from backend",
            trigger: "button[name='open_ui']",
            run: "click",
        },
        Dialog.confirm("Open Register"),
        {
            content: "Open Actions menu",
            trigger: "button.more-btn",
            run: "click",
        },
        {
            content: "Click Refund",
            trigger: "button.btn:contains('Refund')",
            run: "click",
        },
        {
            content: "Select an Order",
            trigger: "div.order-row:contains('Paid')",
            run: "click",
        },
        {
            content: "Select an Orderline",
            trigger: "li.orderline:contains('Test Product 1')",
            run: "click",
        },
        {
            content: "Select qty to refund",
            trigger: "button[value='1']",
            run: "click",
        },
        {
            content: "Select an Orderline",
            trigger: "li.orderline:contains('Discount')",
            run: "click",
        },
        {
            content: "Select qty to refund",
            trigger: "button[value='1']",
            run: "click",
        },
        {
            content: "go to Refund",
            trigger: ".pay-order-button",
            run: "click",
        },
        {
            content: "go to Payment",
            trigger: ".pay-order-button",
            run: "click",
        },
        {
            content: "Click Cash payment method",
            trigger: "div.paymentmethod:contains('Cash')",
            run: "click",
        },
        ...PaymentScreen.clickValidate(),
        Chrome.endTour(),
    ],
});
