import { registry } from "@web/core/registry";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";

registry.category("web_tour.tours").add("test_ec_pos_order_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            [
                {
                    content: "deselect selected partner",
                    trigger: ".modal .partner-info.selected button",
                    run: "click",
                },
            ],
            // Dialog showing the warning that we cannot deselect partner
            Dialog.confirm(),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickDisplayedProduct("Desk Organizer"),
            ProductScreen.totalAmountIs("5.10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickRefund(),
            TicketScreen.search("Customer", "Acme Corporation"),
            TicketScreen.selectOrder("-0001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.customerIsSelected("Acme Corporation"),
            Chrome.endTour(),
        ].flat(),
});
