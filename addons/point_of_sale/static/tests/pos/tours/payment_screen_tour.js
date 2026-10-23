import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
<<<<<<< 377226c20ff988cf7100e3a36d3dd8992e701fbb
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
||||||| 21a6f0411e371cac58514310b78905fcb331c2a9
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "./utils/common";
=======
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { negateStep, refresh } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "./utils/common";
>>>>>>> f6ec8a883a237512026e94a3102381237130599e

registry.category("web_tour.tours").add("PaymentScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            Dialog.cancel(), // Offline mode after opening register will trigger the offline popup since the device try to sync
            ProductScreen.addOrderline("Letter Tray", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.emptyPaymentlines("52.8"),

            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "11", true, {
                amount: "11.00",
                remaining: "41.8",
            }),
            PaymentScreen.validateButtonIsHighlighted(false),
            // remove the selected paymentline with multiple backspace presses
            PaymentScreen.clickNumpad("⌫ ⌫"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "0"),
            PaymentScreen.selectedPaymentlineHas("Cash", "0.00"),
            PaymentScreen.clickPaymentlineDelButton("Cash", "0", true),
            PaymentScreen.emptyPaymentlines("52.8"),

            // Pay with bank, the selected line should have full amount
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            // remove the line using the delete button
            PaymentScreen.clickPaymentlineDelButton("Bank", "52.8"),

            // Use +10 and +50 to increment the amount of the paymentline
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("⌫"),
            PaymentScreen.clickNumpad("+10"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "10"),
            PaymentScreen.remainingIs("42.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickNumpad("5"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "105"),
            PaymentScreen.changeIs("52.2"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickNumpad("+50"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "155"),
            PaymentScreen.changeIs("102.2"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickPaymentlineDelButton("Cash", "155.0"),

            // Multiple paymentlines
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickNumpad("1"),
            PaymentScreen.fillPaymentLineAmountMobile("52.80", "1", 1),
            PaymentScreen.remainingIs("51.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.fillPaymentLineAmountMobile("Bank", "5"),
            PaymentScreen.clickNumpad("5"),
            PaymentScreen.remainingIs("46.8"),
            PaymentScreen.validateButtonIsHighlighted(false),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.validateButtonIsHighlighted(true),
            OfflineUtil.setOnlineMode(),
        ].flat(),
});

registry.category("web_tour.tours").add("PaymentScreenInvoiceOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product Test", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1", true),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            {
                content: "wait for 200 ms",
                trigger: "body",
                run: async () => {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                },
            },
            PaymentScreen.clickValidate(),
            // Edit payment button shouldn't be available for posted orders
            negateStep({ trigger: ".feedback-screen .edit-order-payment:contains(Edit Payment)" }),
            Chrome.clickOrders(),
            TicketScreen.isReady(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            inLeftSide([
                ...Order.hasLine({ productName: "Product Test", withClass: ".selected" }),
                Numpad.click("1"),
            ]),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            {
                content: "invoice button is disabled for refund of an invoiced order",
                trigger: ".js_invoice[disabled]",
            },
            refresh(),
            PaymentScreen.isShown(),
            {
                content: "invoice button is still disabled after refresh",
                trigger: ".js_invoice[disabled]",
            },
        ].flat(),
});
