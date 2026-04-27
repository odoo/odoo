/* global posmodel */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";

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
    steps: () =>
        [
            stepUtils.showAppsMenuItem(),
            {
                content: "Select PoS app",
                trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
                run: "click",
            },
            {
                content: "Start session",
                trigger: ".o_pos_kanban button.oe_kanban_action",
                run: "click",
                expectUnloadPage: true,
            },
            // PART 1: Pay exactly the price of order. Should automatically go to receipt screen.
            {
                content: "confirm dialog",
                trigger: ".modal .modal-footer .btn-primary:contains(Open Register)",
                run: "click",
            },
            {
                content: "Waiting for loading to finish",
                trigger: ".pos .pos-content",
                run: function () {
                    //Overrides the methods inside DeviceController to mock the IoT Box
                    posmodel.models["pos.payment.method"].forEach(function (payment_method) {
                        if (payment_method.terminal_proxy) {
                            payment_method.terminal_proxy = new TerminalProxy();
                        }
                    });
                },
            },
            {
                content: "Buy a Test Product",
                trigger: '.product-list .product-name:contains("Test Product")',
                run: "click",
            },
            ...inLeftSide(Order.hasLine({ productName: "Test Product" })),
            {
                content: "Go to payment screen",
                trigger: ".button.pay-order-button",
                run: "click",
            },
            {
                content: "There should be no payment line",
                trigger: ".paymentlines-empty",
            },
            {
                content: "Pay with payment terminal",
                trigger: '.paymentmethod:contains("Terminal")',
                run: "click",
            },
            {
                content: "Cancel payment",
                trigger: ".button.send_payment_cancel",
                run: "click",
            },
            ...PaymentScreen.clickPaymentlineDelButton("Terminal", "10.00"),
            {
                trigger: ".paymentlines-empty",
            },
            ...PaymentScreen.enterPaymentLineAmount("Terminal", "5", true, { remainingIs: "5.00" }),
            {
                trigger: ".button.send_payment_request.highlight",
                run: "click",
            },
            {
                trigger: ".electronic_status:contains('Successful')",
            },
            ...PaymentScreen.clickPaymentMethod("Cash"),
            ...PaymentScreen.clickNumpad("5"),
            ...PaymentScreen.validateButtonIsHighlighted(),
            ...PaymentScreen.clickValidate(),
            {
                content: "Immediately at the receipt screen.",
                trigger: '.receipt-screen .button.next.highlight:contains("New Order")',
            },
        ].flat(),
});
