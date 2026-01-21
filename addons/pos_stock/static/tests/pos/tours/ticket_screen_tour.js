import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as StockProductScreen from "@pos_stock/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("LotTour", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("1"),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            inLeftSide(
                [
                    StockProductScreen.clickLotIcon(),
                    StockProductScreen.deleteNthLotNumber(1),
                    StockProductScreen.enterLotNumber("2", "serial", true),
                    Order.hasLine({
                        productName: "Product A",
                        quantity: 1,
                    }),
                    StockProductScreen.clickLotIcon(),
                    StockProductScreen.enterLotNumber("1"),
                    Order.hasLine({
                        productName: "Product A",
                        quantity: 2.0,
                    }),
                ].flat()
            ),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("3"),
            ProductScreen.selectedOrderlineHas("Product A", "3"),
            inLeftSide({
                trigger: ".info-list:contains('SN 3')",
            }),

            // Verify if the serial number can be reused for the current order
            Chrome.createFloatingOrder(),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("5"),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("3"),
            inLeftSide({
                trigger: ".info-list:not(:contains('SN 3'))",
            }),
            // Check auto assign lot number if there is only one available option
            ProductScreen.clickDisplayedProduct("Product B"),
            inLeftSide({
                trigger: ".info-list:contains('Lot Number 1001')",
            }),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("002"),
            inLeftSide([Numpad.click("1"), Numpad.click("1")].flat()),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("LotRefundTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickOrders(),
            Chrome.clickOnScanButton(),
            TicketScreen.checkCameraIsOpen(),
            Chrome.clickOnScanButton(),
            Chrome.clickRegister(),
            ProductScreen.clickDisplayedProduct("Product A"),
            StockProductScreen.enterLotNumber("123456789"),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            Chrome.clickOrders(),
            TicketScreen.selectOrder("001"),
            Chrome.clickOnScanButton(),
            TicketScreen.checkCameraIsOpen(),
            Chrome.clickOnScanButton(),
            Chrome.clickRegister(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            StockProductScreen.clickLotIcon(),
            StockProductScreen.checkFirstLotNumber("123456789"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_order_with_existing_serial", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Serial Product"),
            StockProductScreen.enterExistingLotNumber("SN1"),
            ProductScreen.selectedOrderlineHas("Serial Product", "1.00"),
            inLeftSide({
                trigger: ".info-list:contains('SN SN1')",
            }),
            ProductScreen.clickDisplayedProduct("Serial Product"),
            StockProductScreen.enterExistingLotNumber("SN2"),
            ProductScreen.selectedOrderlineHas("Serial Product", "2.00"),
            inLeftSide({
                trigger: ".info-list:contains('SN SN2')",
            }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_lot_refund_lower_qty", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Serial Product"),
            StockProductScreen.enterExistingLotNumbers(["SN1", "SN2"]),
            ProductScreen.selectedOrderlineHas("Serial Product", "2.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.toRefundTextContains("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            {
                trigger: ".info-list:contains('SN SN1')",
            },
            StockProductScreen.clickLotIcon(),
            {
                trigger: ".o-autocomplete--dropdown-item:contains('SN2')",
            },
            Dialog.confirm(),
            {
                content: "go back to the products",
                trigger: ".actionpad .back-button",
                run: "click",
                isActive: ["mobile"],
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            {
                trigger: ".info-list:contains('SN SN2')",
            },
        ].flat(),
});
