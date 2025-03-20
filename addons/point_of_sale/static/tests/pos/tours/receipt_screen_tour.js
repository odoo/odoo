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

registry.category("web_tour.tours").add("ReceiptScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            // press close button in receipt screen
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            ProductScreen.addOrderline("Product for pricelist 6", "10", "5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickShipLaterButton(),
            PaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            Dialog.confirm("Continue with limited functionality"),
            //receipt had expected delivery printed
            ReceiptScreen.shippingDateExists(),
            ReceiptScreen.shippingDateIsToday(),
            // Product for pricelist 6 has 10% tax (search SRC)
            ReceiptScreen.totalAmountContains("55.0"),
            ReceiptScreen.clickNextOrder(),

            // send email in receipt screen
            ProductScreen.addOrderline("Product for pricelist 5", "6", "5", "30.0"),
            ProductScreen.addOrderline("Quality Thing", "6", "6", "36.0"),
            ProductScreen.addOrderline("Product for pricelist 4", "6", "1", "6.0"),
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
            ProductScreen.addOrderline("Product for pricelist 5", "6", "5"),
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
            ProductScreen.addOrderline("Product for pricelist 5", "1", "5"),
            inLeftSide([
                { ...ProductScreen.clickLine("Product for pricelist 5")[0], isActive: ["mobile"] },
                ...ProductScreen.addCustomerNote("Test customer note"),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            Order.hasLine({ customerNote: "Test customer note" }),
            ReceiptScreen.clickNextOrder(),

            // Test discount and original price
            ProductScreen.addOrderline("Product for pricelist 5", "1", "20"),
            inLeftSide([
                { ...ProductScreen.clickLine("Product for pricelist 5")[0], isActive: ["mobile"] },
                Numpad.click("%"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 5", "1", "20"),
                Numpad.click("5"),
                ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 5", "1", "19.0"),
                Numpad.click("."),
            ]),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.receiptIsThere(),
            Order.hasLine({ productName: "Product for pricelist 5", priceNoDiscount: "20" }),
            ReceiptScreen.totalAmountContains("19.00"),
            ReceiptScreen.clickNextOrder(),
            OfflineUtil.setOnlineMode(),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderPaidInCash", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Product for pricelist 5", "5", "5"),
            inLeftSide(ProductScreen.orderLineHas("Product for pricelist 5", "5")),
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
            Chrome.clickBtn("Backend"),
            ProductScreen.lastClosingCashIs("25.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("ReceiptTrackingMethodTour", {
    checkDelay: 50,
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Awesome Article"),
            ProductScreen.enterLotNumber("123456789"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.trackingMethodIsLot(),
        ].flat(),
});
