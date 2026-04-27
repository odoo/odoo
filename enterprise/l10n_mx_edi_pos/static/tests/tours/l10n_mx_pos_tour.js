import { registry } from "@web/core/registry";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as TextInputPopup from "@point_of_sale/../tests/tours/utils/text_input_popup_util";

registry.category("web_tour.tours").add("test_refund_with_gift_card_mx", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.clickControlButton("Enter Code"),
            TextInputPopup.inputText("043123456"),
            Dialog.confirm(),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_refund_with_discount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickControlButton("Discount"),
            Dialog.confirm(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            Dialog.is({ title: "Refund Amount Exceeds Original Order" }),
            Dialog.confirm(),
        ].flat(),
});
