/** @odoo-module */
/* global posmodel */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
class TerminalProxy {
    action(data) {
        var self = this;
        switch (data.messageType) {
            case "Transaction":
                if (!this.transaction) {
                    this.transaction = true;
                    this.cid = data.cid;
                    setTimeout(function () {
                        self.listener({
                            Stage: "WaitingForCard",
                            cid: self.cid,
                        });
                    });
                    this.timer = setTimeout(function () {
                        self.listener({
                            Response: "Approved",
                            Reversal: true,
                            cid: self.cid,
                        });
                        self.transaction = false;
                    }, 1000);
                } else {
                    throw "Another transaction is still running";
                }
                break;
            case "Cancel":
                clearTimeout(this.timer);
                this.transaction = false;
                setTimeout(function () {
                    self.listener({
                        Error: "Canceled",
                        cid: self.cid,
                    });
                });
                break;
        }
        return Promise.resolve({
            result: true,
        });
    }
    addListener(callback) {
        this.listener = callback;
    }
    removeListener() {
        this.listener = false;
    }
}

registry.category("web_tour.tours").add("payment_terminals_tour", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Select PoS app",
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
        },
        {
            content: "Start session",
            trigger: ".o_pos_kanban button.oe_kanban_action_button",
        },
        {
            content: "Waiting for loading to finish",
            trigger: ".pos .pos-content",
            run: function () {
                //Overrides the methods inside DeviceController to mock the IoT Box
                posmodel.payment_methods.forEach(function (payment_method) {
                    if (payment_method.terminal_proxy) {
                        payment_method.terminal_proxy = new TerminalProxy();
                    }
                });
            },
        },
        {
            // PART 1: Pay exactly the price of order. Should automatically go to receipt screen.
            content: "cash control",
            trigger: ".opening-cash-control footer .button",
        },
        ...ProductScreen.clickHomeCategory(),
        {
            content: "Buy a Desk Organizer",
            trigger: '.product-list .product-name:contains("Desk Organizer")',
        },
        ...inLeftSide(Order.hasLine({ productName: "Desk Organizer" })),
        {
            content: "Go to payment screen",
            trigger: ".button.pay-order-button",
        },
        {
            content: "Pay with payment terminal",
            trigger: '.paymentmethod:contains("Terminal")',
        },
        {
            content: "Remove payment line",
            trigger: ".delete-button",
        },
        {
            content: "There should be no payment line",
            trigger: ".paymentlines-empty",
            run: () => {},
        },
        {
            content: "Pay with payment terminal",
            trigger: '.paymentmethod:contains("Terminal")',
        },
        {
            content: "Send payment to terminal",
            trigger: ".button.send_payment_request.highlight",
        },
        {
            content: "Cancel payment",
            trigger: ".button.send_payment_cancel",
        },
        {
            content: "Retry to send payment to terminal",
            trigger: ".button.send_payment_request.highlight",
        },
        {
            content: "Check that the payment is confirmed",
            trigger: ".button.next.highlight",
            run: function () {}, // it's a check
        },
        {
            content: "Immediately at the receipt screen.",
            trigger: '.receipt-screen .button.next.highlight:contains("New Order")',
        },
        {
            // PART 2: Pay more than the order price. Should stay in the payment screen.
            content: "Buy a Desk Organizer",
            trigger: '.product-list .product-name:contains("Desk Organizer")',
        },
        ...Order.hasLine({ prodctName: "Desk Organizer" }),
        {
            content: "Go to payment screen",
            trigger: ".button.pay-order-button",
        },
        {
            content: "Pay with payment terminal",
            trigger: '.paymentmethod:contains("Terminal")',
        },
        Numpad.click("9"),
        {
            content: "Send payment to terminal",
            trigger: ".button.send_payment_request.highlight",
        },
        {
            content: "Check that the payment is confirmed",
            trigger: ".button.next.highlight",
            run: function () {}, // it's a check
        },
        {
            content: "Manually click validate button to get to receipt screen.",
            trigger: '.button.next.highlight:contains("Validate")',
        },
        {
            content: "Check that we're on the receipt screen",
            trigger: '.receipt-screen .button.next.highlight:contains("New Order")',
            run: function () {},
        },
    ],
});
