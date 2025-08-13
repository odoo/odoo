/* global posmodel */

import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import { run, negateStep } from "@point_of_sale/../tests/generic_helpers/utils";
import { renderToElement } from "@web/core/utils/render";
import { formatCurrency } from "@web/core/currency";

registry.category("web_tour.tours").add("ReceiptScreenTour", {
    steps: () =>
        [
            // press close button in receipt screen
            Chrome.startPoS(),
            OfflineUtil.setOfflineMode(),
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
            ReceiptScreen.cashierNameExists("A simple PoS man!"),
            Dialog.confirm("Continue with limited functionality"),
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
            OfflineUtil.setOnlineMode(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            ReceiptScreen.totalAmountContains("72.0"),
            ReceiptScreen.setEmail("test@receiptscreen.com"),
            ReceiptScreen.clickSend(),
            ReceiptScreen.emailIsSuccessful(),
            OfflineUtil.setOfflineMode(),
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

            // Test that Internal notes are not available on receipt
            ProductScreen.addOrderline("Desk Pad", "1", "5"),
            inLeftSide([
                { ...ProductScreen.clickLine("Desk Pad")[0], isActive: ["mobile"] },
                ...ProductScreen.addInternalNote("Test internal note"),
                ...ProductScreen.clickSelectedLine("Desk Pad"),
                ...ProductScreen.addInternalNote("Test internal note on order"),
                ...Order.hasInternalNote("Test internal note on order"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            negateStep(...Order.hasLine({ internalNote: "Test internal note" })),
            negateStep(...Order.hasInternalNote("Test internal note on order")),
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
            OfflineUtil.setOnlineMode(),
        ].flat(),
});

registry.category("web_tour.tours").add("ReceiptScreenDiscountWithPricelistTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Product", "1"),
            ProductScreen.clickPriceList("special_pricelist"),
            inLeftSide(Order.hasLine({ productName: "Test Product", price: "6.30" })),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Order.hasLine({ price: "6.30" }),

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
            ReceiptScreen.trackingMethodIsLot("123456789"),
        ].flat(),
});

registry.category("web_tour.tours").add("point_of_sale.test_printed_receipt_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "5"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            run(() => {
                const line = posmodel.getOrder().lines[0];
                const context = {
                    line,
                    props: { basic_receipt: true },
                    formatCurrency: (amount) => formatCurrency(amount, line.currency.id),
                };

                const rendered = renderToElement("point_of_sale.Orderline", {
                    this: context,
                    ...context,
                });

                if (!rendered.innerHTML.includes("Desk Pad")) {
                    throw new Error("Desk Pad is not present on the ticket");
                }

                if (rendered.innerHTML.includes("5.00 / Units")) {
                    throw new Error("The price should not be included on a basic receipt");
                }
            }, "Basic receipt doesn't have price"),
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
                    posmodel.getOrder().payment_ids[0].setPaymentStatus("force_done");
                },
            },
            {
                trigger: ".send_force_done",
                run: "click",
            },
            ReceiptScreen.receiptIsThere(),
        ].flat(),
});
