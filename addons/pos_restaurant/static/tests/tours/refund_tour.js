import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("RefundStayCurrentTableTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create first order and pay it
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Awesome Article", true, "1"),
            ProductScreen.clickDisplayedProduct("Awesome Article", true, "2"),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.totalAmountIs("40.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),

            // Go to another table and refund one of the products
            FloorScreen.clickTable("4"),
            ProductScreen.orderIsEmpty(),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("001"),
            Order.hasLine({
                productName: "Awesome Article",
            }),
            ProductScreen.clickNumpad("2"),
            TicketScreen.toRefundTextContains("To Refund: 2"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            inLeftSide(ProductScreen.orderLineHas("Awesome Article")),
            ProductScreen.totalAmountIs("-20.00"),
        ].flat(),
});
