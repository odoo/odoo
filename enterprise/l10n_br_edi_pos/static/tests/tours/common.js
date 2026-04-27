import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Notification from "@point_of_sale/../tests/tours/utils/generic_components/notification_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";

function checkReceipt(invoiceNumber) {
    return [
        {
            content: "Receipt should contain sandbox warning",
            trigger:
                ".pos-receipt > div:contains('ISSUED IN SANDBOX ENVIRONMENT - WITHOUT FISCAL VALUE')",
        },
        {
            content: "Receipt should contain header modifications",
            trigger: ".pos-receipt > div:contains('Auxiliary Document of Consumer Invoice')",
        },
        {
            content: "Receipt should contain NFC-e invoice number",
            trigger: `.pos-receipt > div:contains('NFC-e nº ${invoiceNumber}')`,
        },
    ];
}

function checkNoExcludedTaxesProducts() {
    return [
        ProductScreen.searchProduct("Cabinet with doors"),
        {
            content: "Should find no products",
            trigger: ".product-screen:contains('No products found for')",
        },
        {
            content: "Click search more",
            trigger: ".search-more-button > button",
            run: "click",
        },
        Notification.has("No other products found"),
    ].flat();
}

export function generateTour(invoiceNumber, customerName) {
    return [
        Chrome.freezeDateTime(1738796117000),
        Chrome.startPoS(),
        Dialog.confirm("Open Register"),
        ...(customerName
            ? [ProductScreen.clickPartnerButton(), ProductScreen.clickCustomer(customerName)]
            : []),
        ProductScreen.addOrderline("Acoustic Bloc Screens", 3),
        checkNoExcludedTaxesProducts(),
        ProductScreen.clickPayButton(),
        PaymentScreen.clickPaymentMethod("Cash"),
        PaymentScreen.clickValidate(),
        checkReceipt(invoiceNumber),
        Chrome.clickMenuOption("Orders"),
        TicketScreen.selectFilter("All active orders"),
        TicketScreen.selectFilter("Paid"),
        {
            content: "Reprint the receipt",
            trigger: "button:contains('Print Receipt')",
            run: "click",
        },
        checkReceipt(invoiceNumber),
        Chrome.endTour(),
    ].flat();
}
