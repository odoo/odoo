/* global posmodel */
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/tours/utils/common";

registry.category("web_tour.tours").add("ReceiptScreenTour", {
    steps: () =>
        [
            // press close button in receipt screen
            Chrome.startPoS(),
            ProductScreen.addOrderline("Letter Tray", "10", "5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Full"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            //receipt had expected delivery printed
            ReceiptScreen.shippingDateExists(),
            ReceiptScreen.shippingDateIsToday(),
            // letter tray has 10% tax (search SRC)
            ReceiptScreen.totalAmountContains("55.0"),
            ReceiptScreen.clickNextOrder(),

            // send email in receipt screen
            ProductScreen.addOrderline("Desk Pad", "6", "5", "30.0"),
            ProductScreen.addOrderline("Whiteboard Pen", "6", "6", "36.0"),
            ProductScreen.addOrderline("Monitor Stand", "6", "1", "6.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "70", true, { remaining: "2.0" }),
            PaymentScreen.clickNumpad("0"),
            PaymentScreen.fillPaymentLineAmountMobile("Cash", "700"),
            PaymentScreen.changeIs("628.0"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.totalAmountContains("72.0"),
            ReceiptScreen.setEmail("test@receiptscreen.com"),
            ReceiptScreen.clickSend(),
            ReceiptScreen.emailIsSuccessful(),
            ReceiptScreen.clickNextOrder(),

            // order with tip
            // check if tip amount is displayed
            ProductScreen.addOrderline("Desk Pad", "6", "5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickTipButton(),
            {
                content: "click numpad button: 1",
                trigger: ".modal div.numpad button:contains(/^1/)",
                run: "click",
            },
            NumberPopup.isShown("1"),
            Dialog.confirm(),
            PaymentScreen.emptyPaymentlines("31.0"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.totalAmountContains(`$ 30.00 + $ 1.00 tip`),
            ReceiptScreen.clickNextOrder(),

            // Test customer note in receipt
            ProductScreen.addOrderline("Desk Pad", "1", "5"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Order.hasLine({ customerNote: "Test customer note" }),
            ReceiptScreen.clickNextOrder(),

            // Test discount and original price
            ProductScreen.addOrderline("Desk Pad", "1", "20"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                Numpad.click("%"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1", "20"),
                Numpad.click("5"),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1", "19.0"),
                Numpad.click("."),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            Order.hasLine({ productName: "Desk Pad", priceNoDiscount: "20" }),
            ReceiptScreen.totalAmountContains("19.00"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("ReceiptScreenDiscountWithPricelistTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Product", "1"),
            ProductScreen.clickPriceList("special_pricelist"),
            inLeftSide(Order.hasLine({ productName: "Test Product", oldPrice: "7.0" })),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Order.hasLine({ oldPrice: "7" }),

            ReceiptScreen.clickNextOrder(),
            ProductScreen.addOrderline("Test Product", "1"),
            inLeftSide([
                { ...ProductScreen.clickLine("Test Product")[0], isActive: ["mobile"] },
                Numpad.click("Price"),
                Numpad.isActive("Price"),
                Numpad.click("9"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.noDiscountAmount(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderPaidInCash", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "5", "5"),
            inLeftSide(ProductScreen.orderLineHas("Desk Pad", "5")),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.isShown(),
            // Close the session
            Chrome.clickMenuOption("Close Register"),
            ProductScreen.closeWithCashAmount("25"),
            ProductScreen.cashDifferenceIs("0.00"),
            Dialog.confirm("Close Register"),
            {
                trigger: "button:contains(backend)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: "body",
                expectUnloadPage: true,
            },
            ProductScreen.lastClosingCashIs("25.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("ReceiptTrackingMethodTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.trackingMethodIsLot(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_auto_validate_force_done", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            {
                trigger: "body",
                run: () => {
                    posmodel.get_order().payment_ids[0].set_payment_status("force_done");
                },
            },
            {
                trigger: ".send_force_done",
                run: "click",
            },
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
